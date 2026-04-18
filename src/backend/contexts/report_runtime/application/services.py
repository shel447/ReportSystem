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
from ...template_catalog.domain.models import ReportTemplate
from ..domain.models import TemplateInstance
from ..domain.services import serialize_template_instance

REPORT_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "report.schema.json"
REPORT_SCHEMA = json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))
REPORT_VALIDATOR = Draft202012Validator(REPORT_SCHEMA)


class ReportRuntimeService:
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
        template_instance = self.template_instance_repository.get(template_instance_id, user_id=user_id)
        if template_instance is None:
            raise NotFoundError("Template instance not found")
        template = self.template_repository.get_by_id(template_instance.template_id)
        if template is None:
            raise NotFoundError("Template not found")

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
        self.get_report_view(report_id, user_id=user_id)
        document = self.document_repository.get_for_report(report_id, document_id)
        if document is None:
            raise NotFoundError("Document not found")
        metadata, absolute_path = self.document_gateway.resolve_download(document)
        return metadata, absolute_path

    def serialize_report_answer(self, *, instance, template_instance: TemplateInstance) -> dict[str, Any]:
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
    def __init__(self, *, runtime_service: ReportRuntimeService) -> None:
        self.runtime_service = runtime_service

    def resolve_download(self, *, report_id: str, document_id: str, user_id: str) -> tuple[dict[str, Any], str]:
        return self.runtime_service.resolve_download(report_id=report_id, document_id=document_id, user_id=user_id)


def build_report_dsl(*, report_id: str, template: ReportTemplate, template_instance: TemplateInstance) -> dict[str, Any]:
    catalogs = []
    report_meta: dict[str, Any] = {}
    init_telecom_demo_db()

    for catalog in template_instance.catalogs:
        section_payloads = []
        for section in catalog.get("sections") or []:
            components, summary, additional_infos = _build_section_components(section)
            section_payloads.append(
                {
                    "id": section.get("id"),
                    "title": section.get("title"),
                    "order": section.get("order") or 1,
                    "components": components,
                    "summary": {
                        "id": f"summary_{section.get('id')}",
                        "overview": summary,
                    },
                }
            )
            report_meta[str(section.get("id"))] = {
                "status": "Success",
                "question": str((section.get("requirementInstance") or {}).get("text") or ""),
                "additionalInfos": additional_infos,
            }
        catalogs.append(
            {
                "id": catalog.get("id"),
                "name": catalog.get("name"),
                "order": catalog.get("order") or 1,
                "sections": section_payloads,
            }
        )

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


def _build_section_components(section: dict[str, Any]) -> tuple[list[dict[str, Any]], str, list[dict[str, Any]]]:
    requirement_text = str((section.get("requirementInstance") or {}).get("text") or "")
    datasets = []
    additional_infos = []
    for binding in list(section.get("executionBindings") or []):
        resolved_query = str(binding.get("resolvedQuery") or "").strip()
        if resolved_query:
            additional_infos.append({"type": "SQL", "value": resolved_query})

    # Current implementation compiles deterministic markdown/text content from the requirement and resolved values.
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
    summary = requirement_text or str(section.get("title") or "")
    return components, summary[:160], additional_infos


def _build_markdown_content(section: dict[str, Any], requirement_text: str) -> str:
    lines = [f"## {section.get('title') or ''}".strip(), "", requirement_text or "本章节基于模板诉求自动生成。", ""]
    items = ((section.get("requirementInstance") or {}).get("items") or [])
    if items:
        lines.append("### 诉求要素")
        lines.append("")
        for item in items:
            values = [str(value.get("display") or value.get("value") or "") for value in item.get("resolvedValues") or []]
            rendered = "、".join([value for value in values if value]) or "未设置"
            lines.append(f"- {item.get('label')}: {rendered}")
        lines.append("")
    lines.append("### 生成说明")
    lines.append("")
    lines.append("当前实现按正式模板实例生成报告 DSL，并保留诉求文本与执行绑定证据。")
    return "\n".join(lines).strip()


def _build_report_name(*, template: ReportTemplate, template_instance: TemplateInstance) -> str:
    first_values = []
    for values in template_instance.parameter_values.values():
        if values:
            first_values.append(str(values[0].get("display") or values[0].get("value") or ""))
        if len(first_values) >= 2:
            break
    suffix = " ".join([value for value in first_values if value])
    if suffix:
        return f"{suffix} {template.name}".strip()
    return template.name


def _build_report_summary(catalogs: list[dict[str, Any]]) -> str:
    section_titles = [
        str(section.get("title") or "")
        for catalog in catalogs
        for section in list(catalog.get("sections") or [])
        if str(section.get("title") or "").strip()
    ]
    if not section_titles:
        return "报告已生成。"
    return f"报告已生成，共包含 {len(section_titles)} 个章节：{'、'.join(section_titles[:5])}"


def _resource_status_from_dsl(report: dict[str, Any]) -> str:
    status = str((((report.get("basicInfo") or {}).get("status")) or "")).strip()
    if status == "Running":
        return "generating"
    if status == "Failed":
        return "failed"
    return "available"


def _build_generation_progress(report: dict[str, Any]) -> dict[str, int]:
    total = sum(len(list(catalog.get("sections") or [])) for catalog in list(report.get("catalogs") or []))
    return {"totalSections": total, "completedSections": total}


def _validate_report_dsl(report: dict[str, Any]) -> None:
    errors = sorted(REPORT_VALIDATOR.iter_errors(report), key=lambda item: list(item.absolute_path))
    if not errors:
        return
    error = errors[0]
    path = ".".join(str(part) for part in error.absolute_path)
    if path:
        raise ValidationError(f"报告 DSL 校验失败: {path} {error.message}")
    raise ValidationError(f"报告 DSL 校验失败: {error.message}")
