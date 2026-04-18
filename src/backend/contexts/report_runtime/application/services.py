"""报告运行时应用服务，负责将模板实例冻结为报告和导出文档。"""

from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from ....infrastructure.demo.telecom import get_demo_db_path, init_telecom_demo_db
from ....shared.kernel.errors import NotFoundError, ValidationError
from ...template_catalog.infrastructure.schema import validate_template_instance
from ...template_catalog.domain.models import ReportTemplate
from ..domain.models import TemplateInstance
from ..domain.services import serialize_template_instance

REPORT_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "report.schema.json"
REPORT_SCHEMA = json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))
REPORT_VALIDATOR = Draft202012Validator(REPORT_SCHEMA)


class ReportRuntimeService:
    """负责模板实例冻结与报告导出的应用服务。"""

    def __init__(
        self,
        *,
        template_repository,
        template_instance_repository,
        report_instance_repository,
        document_repository,
        export_job_repository,
        document_gateway,
    ) -> None:
        self.template_repository = template_repository
        self.template_instance_repository = template_instance_repository
        self.report_instance_repository = report_instance_repository
        self.document_repository = document_repository
        self.export_job_repository = export_job_repository
        self.document_gateway = document_gateway

    def persist_template_instance(self, instance: TemplateInstance, *, user_id: str) -> dict[str, Any]:
        """创建或更新流程中唯一被跟踪的模板实例。"""
        serialized = serialize_template_instance(instance)
        try:
            validate_template_instance(serialized)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        existing = self.template_instance_repository.get(instance.id, user_id=user_id)
        saved = (
            self.template_instance_repository.update(instance, user_id=user_id)
            if existing
            else self.template_instance_repository.create(instance, user_id=user_id)
        )
        return serialize_template_instance(saved)

    def get_latest_template_instance(self, *, conversation_id: str, user_id: str) -> dict[str, Any] | None:
        instance = self.template_instance_repository.get_latest_for_conversation(conversation_id, user_id=user_id)
        if instance is None:
            return None
        return serialize_template_instance(instance)

    def generate_report_from_template_instance(
        self,
        *,
        template_instance_id: str,
        user_id: str,
        source_conversation_id: str | None,
        source_chat_id: str | None,
    ) -> dict[str, Any]:
        """将已确认的模板实例冻结为正式报告结构与报告资源。"""
        template_instance = self.template_instance_repository.get(template_instance_id, user_id=user_id)
        if template_instance is None:
            raise NotFoundError("Template instance not found")
        template_payload = copy.deepcopy(template_instance.template or {})
        if not template_payload:
            template = self.template_repository.get_by_id(template_instance.template_id)
            if template is None:
                raise NotFoundError("Template not found")
            template_payload = {
                "id": template.id,
                "category": template.category,
                "name": template.name,
                "description": template.description,
                "schemaVersion": template.schema_version,
                "parameters": copy.deepcopy(template.parameters),
                "catalogs": copy.deepcopy(template.catalogs),
                "tags": copy.deepcopy(template.tags),
            }
        template = ReportTemplate(
            id=str(template_payload.get("id") or template_instance.template_id),
            category=str(template_payload.get("category") or ""),
            name=str(template_payload.get("name") or ""),
            description=str(template_payload.get("description") or ""),
            schema_version=str(template_payload.get("schemaVersion") or "template.v3"),
            parameters=list(template_payload.get("parameters") or []),
            catalogs=list(template_payload.get("catalogs") or []),
            tags=list(template_payload.get("tags") or []),
        )

        report_id = f"rpt_{uuid.uuid4().hex[:12]}"
        report = build_report_dsl(report_id=report_id, template=template, template_instance=template_instance)
        _validate_report_dsl(report)
        resource_status = _resource_status_from_dsl(report)
        instance = self.report_instance_repository.create(
            report_id=report_id,
            template_id=template.id,
            template_instance_id=template_instance.id,
            user_id=user_id,
            source_conversation_id=source_conversation_id,
            source_chat_id=source_chat_id,
            status=resource_status,
            schema_version=report["basicInfo"]["schemaVersion"],
            report=report,
        )
        template_instance.status = "completed"
        template_instance.capture_stage = "report_ready"
        updated_template_instance = self.template_instance_repository.update(template_instance, user_id=user_id)
        return self.serialize_report_answer(instance=instance, template_instance=updated_template_instance)

    def get_report_view(self, report_id: str, *, user_id: str) -> dict[str, Any]:
        """返回公开的报告聚合视图。"""
        instance = self.report_instance_repository.get(report_id, user_id=user_id)
        if instance is None:
            raise NotFoundError("Report not found")
        template_instance = self.template_instance_repository.get(instance.template_instance_id, user_id=user_id)
        if template_instance is None:
            raise NotFoundError("Template instance not found")
        return {
            "reportId": instance.id,
            "status": instance.status,
            "answerType": "REPORT",
            "answer": self.serialize_report_answer(instance=instance, template_instance=template_instance),
        }

    def generate_documents(
        self,
        *,
        report_id: str,
        user_id: str,
        formats: list[str],
        pdf_source: str | None,
        theme: str,
        strict_validation: bool,
        regenerate_if_exists: bool,
    ) -> dict[str, Any]:
        """生成报告作用域下的文档产物及对应导出任务。"""
        report_view = self.get_report_view(report_id, user_id=user_id)
        answer = report_view["answer"]
        existing_documents = self.document_repository.list_by_report(report_id)
        reusable_documents = [] if regenerate_if_exists else [self.document_gateway.serialize_document(item) for item in existing_documents]
        jobs = []
        new_documents = []

        request_hash = hashlib.sha1(
            json.dumps(
                {
                    "formats": formats,
                    "pdfSource": pdf_source,
                    "theme": theme,
                    "strictValidation": strict_validation,
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()

        dependency_job_id = None
        for format_name in formats:
            # 导出任务只负责记录编排顺序，实际文件生成下沉到文档网关。
            job = self.export_job_repository.create(
                report_instance_id=report_id,
                current_format=format_name,
                status="queued",
                dependency_job_id=dependency_job_id,
                exporter_backend="java_office_exporter" if format_name in {"word", "ppt", "pdf"} else "local_markdown",
                request_payload_hash=request_hash,
            )
            jobs.append(
                {
                    "jobId": job.id,
                    "format": format_name,
                    "status": "queued" if dependency_job_id is None else "blocked_by_dependency",
                    "dependsOn": dependency_job_id,
                }
            )
            artifact = self.document_gateway.generate_document(
                report=answer["report"],
                report_id=report_id,
                format_name=format_name,
                theme=theme,
                strict_validation=strict_validation,
                pdf_source=pdf_source,
            )
            document = self.document_repository.create(
                report_instance_id=report_id,
                artifact_kind=format_name,
                source_format=pdf_source if format_name == "pdf" else None,
                generation_mode="sync",
                mime_type=artifact["mimeType"],
                storage_key=artifact["storageKey"],
                status="ready",
            )
            new_documents.append(self.document_gateway.serialize_document(document))
            dependency_job_id = job.id if format_name in {"word", "ppt"} else dependency_job_id

        return {
            "reportId": report_id,
            "jobs": jobs,
            "documents": reusable_documents + new_documents,
        }

    def resolve_download(self, *, report_id: str, document_id: str, user_id: str) -> tuple[dict[str, Any], str]:
        """在不暴露独立文档资源的前提下解析报告范围下载。"""
        self.get_report_view(report_id, user_id=user_id)
        document = self.document_repository.get_for_report(report_id, document_id)
        if document is None:
            raise NotFoundError("Document not found")
        metadata, absolute_path = self.document_gateway.resolve_download(document)
        return metadata, absolute_path

    def serialize_report_answer(self, *, instance, template_instance: TemplateInstance) -> dict[str, Any]:
        """保持聊天报告响应与报告详情载荷结构一致。"""
        documents = [self.document_gateway.serialize_document(item) for item in self.document_repository.list_by_report(instance.id)]
        return {
            "reportId": instance.id,
            "status": instance.status,
            "report": copy.deepcopy(instance.report),
            "templateInstance": serialize_template_instance(template_instance),
            "documents": documents,
            "generationProgress": _build_generation_progress(instance.report),
        }


class ReportDocumentService:
    """面向报告范围文档下载的轻量应用门面。"""

    def __init__(self, *, runtime_service: ReportRuntimeService) -> None:
        self.runtime_service = runtime_service

    def resolve_download(self, *, report_id: str, document_id: str, user_id: str) -> tuple[dict[str, Any], str]:
        return self.runtime_service.resolve_download(report_id=report_id, document_id=document_id, user_id=user_id)


def build_report_dsl(*, report_id: str, template: ReportTemplate, template_instance: TemplateInstance) -> dict[str, Any]:
    """把已确认的模板实例编译成正式报告载荷。"""
    catalogs = []
    report_meta: dict[str, Any] = {}
    init_telecom_demo_db()

    for catalog in template_instance.catalogs:
        catalogs.append(_build_report_catalog(catalog, report_meta))

    report_name = _build_report_name(template=template, template_instance=template_instance)
    today = datetime.now(timezone.utc).date().isoformat()
    report = {
        "basicInfo": {
            "id": report_id,
            "schemaVersion": "1.0.0",
            "mode": "published",
            "status": "Success",
            "name": report_name,
            "subTitle": today,
            "description": template.description,
            "templateId": template.id,
            "templateName": template.name,
            "version": "1.0.0",
            "createDate": today,
            "modifyDate": today,
            "creator": "report-system",
            "modifier": "report-system",
            "category": template.category,
        },
        "catalogs": catalogs,
        "summary": {
            "id": "summary_report",
            "overview": _build_report_summary(catalogs),
        },
        "reportMeta": report_meta,
        "layout": {"type": "grid", "grid": {"cols": 12, "rowHeight": 24}},
    }
    return report


def _build_report_catalog(catalog: dict[str, Any], report_meta: dict[str, Any]) -> dict[str, Any]:
    built = {
        "id": catalog.get("id"),
        "name": catalog.get("renderedTitle") or catalog.get("title") or catalog.get("id"),
    }
    sub_catalogs = [_build_report_catalog(sub_catalog, report_meta) for sub_catalog in list(catalog.get("subCatalogs") or [])]
    sections = []
    for section in list(catalog.get("sections") or []):
        components, summary, additional_infos = _build_section_components(section)
        section_payload = {
            "id": section.get("id"),
            "title": _section_title(section),
            "components": components,
            "summary": {
                "id": f"summary_{section.get('id')}",
                "overview": summary,
            },
        }
        sections.append(section_payload)
        report_meta[str(section.get("id"))] = {
            "status": "Success",
            "question": str(((section.get("outline") or {}).get("renderedRequirement")) or ((section.get("outline") or {}).get("requirement")) or ""),
            "additionalInfos": additional_infos,
        }
    if sub_catalogs:
        built["subCatalogs"] = sub_catalogs
    if sections:
        built["sections"] = sections
    return built


def _build_section_components(section: dict[str, Any]) -> tuple[list[dict[str, Any]], str, list[dict[str, Any]]]:
    outline = section.get("outline") if isinstance(section.get("outline"), dict) else {}
    requirement_text = str(outline.get("renderedRequirement") or outline.get("requirement") or "")
    additional_infos = []
    for binding in list((((section.get("runtimeContext") or {}).get("bindings")) or [])):
        resolved_query = str(binding.get("resolvedQuery") or "").strip()
        if resolved_query:
            additional_infos.append({"type": "SQL", "value": resolved_query})

    # 当前运行时保持确定性生成：把正式诉求状态编译成文稿区块，
    # 并把已解析的执行绑定作为证据写入附加信息。
    components = [
        {
            "id": f"component_{section.get('id')}_markdown",
            "type": "markdown",
            "dataProperties": {
                "dataType": "static",
                "content": _build_markdown_content(section, requirement_text),
            },
        }
    ]
    summary = requirement_text or str(section.get("id") or "")
    return components, summary[:160], additional_infos


def _build_markdown_content(section: dict[str, Any], requirement_text: str) -> str:
    lines = [f"## {_section_title(section)}".strip(), "", requirement_text or "本章节基于模板诉求自动生成。", ""]
    items = ((section.get("outline") or {}).get("items") or [])
    if items:
        lines.append("### 诉求要素")
        lines.append("")
        for item in items:
            values = [str(value.get("display") or value.get("value") or "") for value in item.get("values") or []]
            rendered = "、".join([value for value in values if value]) or "未设置"
            lines.append(f"- {item.get('label')}: {rendered}")
        lines.append("")
    lines.append("### 生成说明")
    lines.append("")
    lines.append("当前实现按正式模板实例生成报告 DSL，并保留诉求文本与执行绑定证据。")
    return "\n".join(lines).strip()


def _section_title(section: dict[str, Any]) -> str:
    outline = section.get("outline") if isinstance(section.get("outline"), dict) else {}
    rendered_requirement = str(outline.get("renderedRequirement") or outline.get("requirement") or "").strip()
    if not rendered_requirement:
        return str(section.get("id") or "")
    return rendered_requirement[:80]


def _build_report_name(*, template: ReportTemplate, template_instance: TemplateInstance) -> str:
    first_values = []
    for parameter in template_instance.parameters:
        values = parameter.get("values") or []
        if values:
            first_values.append(str(values[0].get("display") or values[0].get("value") or ""))
        if len(first_values) >= 2:
            break
    suffix = " ".join([value for value in first_values if value])
    if suffix:
        return f"{suffix} {template.name}".strip()
    return template.name


def _build_report_summary(catalogs: list[dict[str, Any]]) -> str:
    section_titles = _collect_section_titles(catalogs)
    if not section_titles:
        return "报告已生成。"
    return f"报告已生成，共包含 {len(section_titles)} 个章节：{'、'.join(section_titles[:5])}"


def _collect_section_titles(catalogs: list[dict[str, Any]]) -> list[str]:
    titles: list[str] = []
    for catalog in catalogs:
        for section in list(catalog.get("sections") or []):
            title = str(section.get("title") or "").strip()
            if title:
                titles.append(title)
        titles.extend(_collect_section_titles(list(catalog.get("subCatalogs") or [])))
    return titles


def _count_catalogs(catalogs: list[dict[str, Any]]) -> int:
    total = 0
    for catalog in catalogs:
        total += 1
        total += _count_catalogs(list(catalog.get("subCatalogs") or []))
    return total


def _resource_status_from_dsl(report: dict[str, Any]) -> str:
    status = str((((report.get("basicInfo") or {}).get("status")) or "")).strip()
    if status == "Running":
        return "generating"
    if status == "Failed":
        return "failed"
    return "available"


def _build_generation_progress(report: dict[str, Any]) -> dict[str, int]:
    total_sections = len(_collect_section_titles(list(report.get("catalogs") or [])))
    total_catalogs = _count_catalogs(list(report.get("catalogs") or []))
    return {
        "totalSections": total_sections,
        "completedSections": total_sections,
        "totalCatalogs": total_catalogs,
        "completedCatalogs": total_catalogs,
    }


def _validate_report_dsl(report: dict[str, Any]) -> None:
    """若冻结后的报告不再满足公开结构约束，则立即失败。"""
    errors = sorted(REPORT_VALIDATOR.iter_errors(report), key=lambda item: list(item.absolute_path))
    if not errors:
        return
    error = errors[0]
    path = ".".join(str(part) for part in error.absolute_path)
    if path:
        raise ValidationError(f"报告 DSL 校验失败: {path} {error.message}")
    raise ValidationError(f"报告 DSL 校验失败: {error.message}")
