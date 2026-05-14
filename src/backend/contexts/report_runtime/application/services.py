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
from ...template_catalog.domain.models import (
    Parameter,
    parameter_value_to_dict,
    ReportTemplate,
)
from .models import (
    DocumentGenerationJobView,
    DocumentGenerationResult,
    DownloadResolution,
    GenerationProgressView,
    ReportAnswerView,
    ReportView,
)
from ..domain.models import (
    ChartComponent,
    ChartDataProperties,
    CompositeTableComponent,
    CompositeTableDataProperties,
    MarkdownComponent,
    MarkdownDataProperties,
    ReportAdditionalInfo,
    ReportBasicInfo,
    ReportCatalog,
    ReportColumn,
    ReportDsl,
    ReportGenerateMeta,
    ReportLayout,
    MergeRowInfo,
    ReportSection,
    ReportSummary,
    TableComponent,
    TableDataProperties,
    TemplateInstance,
    TextComponent,
    TextDataProperties,
    GridDefinition,
    ReportInstance,
    report_catalog_from_dict,
    report_dsl_to_dict,
    report_section_from_dict,
)
from ..domain.services import serialize_template_instance

REPORT_SCHEMA_PATH = Path(__file__).resolve().parents[5] / "design" / "report_system" / "schemas" / "report-dsl.schema.json"
REPORT_SCHEMA = json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))
REPORT_VALIDATOR = Draft202012Validator(REPORT_SCHEMA)
REPORT_CATALOG_FRAGMENT_VALIDATOR = Draft202012Validator(
    {
        "$schema": REPORT_SCHEMA.get("$schema"),
        "$defs": REPORT_SCHEMA.get("$defs", {}),
        "$ref": "#/$defs/Catalog",
    }
)
REPORT_SECTION_FRAGMENT_VALIDATOR = Draft202012Validator(
    {
        "$schema": REPORT_SCHEMA.get("$schema"),
        "$defs": REPORT_SCHEMA.get("$defs", {}),
        "$ref": "#/$defs/Section",
    }
)


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
        custom_content_gateway=None,
    ) -> None:
        self.template_repository = template_repository
        self.template_instance_repository = template_instance_repository
        self.report_instance_repository = report_instance_repository
        self.document_repository = document_repository
        self.export_job_repository = export_job_repository
        self.document_gateway = document_gateway
        self.custom_content_gateway = custom_content_gateway

    def persist_template_instance(self, instance: TemplateInstance, *, user_id: str) -> TemplateInstance:
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
        return saved

    def get_latest_template_instance(self, *, conversation_id: str, user_id: str) -> TemplateInstance | None:
        instance = self.template_instance_repository.get_latest_for_conversation(conversation_id, user_id=user_id)
        return instance

    def generate_report_from_template_instance(
        self,
        *,
        template_instance_id: str,
        user_id: str,
        source_conversation_id: str | None,
        source_chat_id: str | None,
    ) -> ReportAnswerView:
        """将已确认的模板实例冻结为正式报告结构与报告资源。"""
        template_instance = self.template_instance_repository.get(template_instance_id, user_id=user_id)
        if template_instance is None:
            raise NotFoundError("Template instance not found")
        template_model = copy.deepcopy(template_instance.template)
        if not template_model.id:
            template = self.template_repository.get_by_id(template_instance.template_id)
            if template is None:
                raise NotFoundError("Template not found")
            template_model = copy.deepcopy(template)

        report_id = f"rpt_{uuid.uuid4().hex[:12]}"
        report = build_report_dsl(
            report_id=report_id,
            template=template_model,
            template_instance=template_instance,
            custom_content_gateway=self.custom_content_gateway,
        )
        report_payload = report_dsl_to_dict(report)
        _validate_report_dsl(report_payload)
        resource_status = _resource_status_from_dsl(report)
        instance = self.report_instance_repository.create(
            report_id=report_id,
            template_id=template_model.id,
            template_instance_id=template_instance.id,
            user_id=user_id,
            source_conversation_id=source_conversation_id,
            source_chat_id=source_chat_id,
            status=resource_status,
            schema_version=report.basic_info.schema_version or "1.0.0",
            report=report,
        )
        template_instance.status = "completed"
        template_instance.capture_stage = "report_ready"
        updated_template_instance = self.template_instance_repository.update(template_instance, user_id=user_id)
        return self.serialize_report_answer(instance=instance, template_instance=updated_template_instance)

    def get_report_view(self, report_id: str, *, user_id: str) -> ReportView:
        """返回公开的报告聚合视图。"""
        instance = self.report_instance_repository.get(report_id, user_id=user_id)
        if instance is None:
            raise NotFoundError("Report not found")
        template_instance = self.template_instance_repository.get(instance.template_instance_id, user_id=user_id)
        if template_instance is None:
            raise NotFoundError("Template instance not found")
        return ReportView(
            report_id=instance.id,
            status=instance.status,
            answer_type="REPORT",
            answer=self.serialize_report_answer(instance=instance, template_instance=template_instance),
        )

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
    ) -> DocumentGenerationResult:
        """生成报告作用域下的文档产物及对应导出任务。"""
        report_view = self.get_report_view(report_id, user_id=user_id)
        answer = report_view.answer
        existing_documents = self.document_repository.list_by_report(report_id)
        reusable_documents = [] if regenerate_if_exists else [self.document_gateway.serialize_document(item) for item in existing_documents]
        jobs: list[DocumentGenerationJobView] = []
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
                DocumentGenerationJobView(
                    job_id=job.id,
                    format=format_name,
                    status="queued" if dependency_job_id is None else "blocked_by_dependency",
                    depends_on=dependency_job_id,
                )
            )
            artifact = self.document_gateway.generate_document(
                report=answer.report,
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
                mime_type=artifact.mime_type,
                storage_key=artifact.storage_key,
                status="ready",
            )
            new_documents.append(self.document_gateway.serialize_document(document))
            dependency_job_id = job.id if format_name in {"word", "ppt"} else dependency_job_id

        return DocumentGenerationResult(report_id=report_id, jobs=jobs, documents=reusable_documents + new_documents)

    def resolve_download(self, *, report_id: str, document_id: str, user_id: str) -> DownloadResolution:
        """在不暴露独立文档资源的前提下解析报告范围下载。"""
        self.get_report_view(report_id, user_id=user_id)
        document = self.document_repository.get_for_report(report_id, document_id)
        if document is None:
            raise NotFoundError("Document not found")
        return self.document_gateway.resolve_download(document)

    def serialize_report_answer(self, *, instance: ReportInstance, template_instance: TemplateInstance) -> ReportAnswerView:
        """保持聊天报告响应与报告详情载荷结构一致。"""
        documents = [self.document_gateway.serialize_document(item) for item in self.document_repository.list_by_report(instance.id)]
        return ReportAnswerView(
            report_id=instance.id,
            status=instance.status,
            report=instance.report,
            template_instance=template_instance,
            documents=documents,
            generation_progress=_build_generation_progress(instance.report),
        )


class ReportDocumentService:
    """面向报告范围文档下载的轻量应用门面。"""

    def __init__(self, *, runtime_service: ReportRuntimeService) -> None:
        self.runtime_service = runtime_service

    def resolve_download(self, *, report_id: str, document_id: str, user_id: str) -> DownloadResolution:
        return self.runtime_service.resolve_download(report_id=report_id, document_id=document_id, user_id=user_id)


def build_report_dsl(
    *,
    report_id: str,
    template: ReportTemplate,
    template_instance: TemplateInstance,
    custom_content_gateway=None,
) -> ReportDsl:
    """把已确认的模板实例编译成正式报告载荷。"""
    catalogs: list[ReportCatalog] = []
    report_meta: dict[str, ReportGenerateMeta] = {}
    init_telecom_demo_db()

    for catalog in template_instance.catalogs:
        catalogs.append(
            _build_report_catalog(
                catalog,
                report_meta,
                custom_content_gateway=custom_content_gateway,
                inherited_parameters={},
            )
        )

    report_name = _build_report_name(template=template, template_instance=template_instance)
    today = datetime.now(timezone.utc).date().isoformat()
    return ReportDsl(
        structure_type="flow",
        basic_info=ReportBasicInfo(
            id=report_id,
            schema_version="1.0.0",
            status="Success",
            name=report_name,
            title=today,
            description=template.description,
            template_id=template.id,
            template_name=template.name,
            created_at=f"{today}T00:00:00Z",
            updated_at=f"{today}T00:00:00Z",
            creator="report-system",
            modifier="report-system",
            category=template.category,
        ),
        catalogs=catalogs,
        summary=ReportSummary(id="summary_report", overview=_build_report_summary(catalogs)),
        report_meta=report_meta,
        layout=ReportLayout(type="grid", grid=GridDefinition(cols=12, row_height=24)),
    )


def _build_report_catalog(
    catalog,
    report_meta: dict[str, ReportGenerateMeta],
    *,
    custom_content_gateway=None,
    inherited_parameters: dict[str, list[dict[str, Any]]] | None = None,
) -> ReportCatalog:
    visible_parameters = _merge_parameter_payloads(inherited_parameters or {}, list(catalog.parameters or []))
    if _is_custom_context(catalog.dynamic_context, "catalog"):
        prompt = str(catalog.rendered_title or catalog.title or catalog.id or "")
        custom_catalog = _fetch_custom_catalog(
            gateway=custom_content_gateway,
            url=str(catalog.dynamic_context.url or ""),
            node_id=str(catalog.id or ""),
            parameters=visible_parameters,
            prompt=prompt,
        )
        _record_custom_catalog_meta(custom_catalog, report_meta, prompt=prompt)
        return custom_catalog

    sub_catalogs = [
        _build_report_catalog(
            sub_catalog,
            report_meta,
            custom_content_gateway=custom_content_gateway,
            inherited_parameters=visible_parameters,
        )
        for sub_catalog in list(catalog.sub_catalogs or [])
    ]
    sections: list[ReportSection] = []
    for section in list(catalog.sections or []):
        section_parameters = _merge_parameter_payloads(visible_parameters, list(section.parameters or []))
        if _is_custom_context(section.dynamic_context, "section"):
            prompt = str(section.outline.rendered_requirement or section.outline.requirement or "")
            custom_section = _fetch_custom_section(
                gateway=custom_content_gateway,
                url=str(section.dynamic_context.url or ""),
                node_id=str(section.id or ""),
                parameters=section_parameters,
                prompt=prompt,
            )
            sections.append(custom_section)
            report_meta[custom_section.id] = ReportGenerateMeta(status="Success", question=prompt, additional_infos=[])
            continue
        components, summary, additional_infos = _build_section_components(section)
        sections.append(
            ReportSection(
                id=section.id,
                title=_section_title(section),
                components=components,
                summary=ReportSummary(
                    id=f"summary_{section.id}",
                    overview=summary,
                ),
            )
        )
        report_meta[section.id] = ReportGenerateMeta(
            status="Success",
            question=section.outline.rendered_requirement or section.outline.requirement or "",
            additional_infos=[
                ReportAdditionalInfo(type="Summary", value=summary),
                *additional_infos,
            ],
        )
    return ReportCatalog(
        id=catalog.id,
        name=catalog.rendered_title or catalog.title or catalog.id,
        sub_catalogs=sub_catalogs,
        sections=sections,
    )


def _is_custom_context(dynamic_context, expected_node_type: str) -> bool:
    if dynamic_context is None or dynamic_context.type != "custom":
        return False
    node_type = str(dynamic_context.node_type or expected_node_type)
    return node_type == expected_node_type


def _merge_parameter_payloads(
    inherited: dict[str, list[dict[str, Any]]],
    parameters: list[Parameter],
) -> dict[str, list[dict[str, Any]]]:
    merged = copy.deepcopy(inherited)
    for parameter in parameters:
        merged[str(parameter.id or "")] = [parameter_value_to_dict(value) for value in list(parameter.values or [])]
    return merged


def _fetch_custom_catalog(
    *,
    gateway,
    url: str,
    node_id: str,
    parameters: dict[str, list[dict[str, Any]]],
    prompt: str,
) -> ReportCatalog:
    payload = _fetch_custom_payload(gateway=gateway, url=url, node_type="catalog", node_id=node_id, parameters=parameters, prompt=prompt)
    _validate_report_fragment(REPORT_CATALOG_FRAGMENT_VALIDATOR, payload, "custom catalog")
    return report_catalog_from_dict(payload)


def _fetch_custom_section(
    *,
    gateway,
    url: str,
    node_id: str,
    parameters: dict[str, list[dict[str, Any]]],
    prompt: str,
) -> ReportSection:
    payload = _fetch_custom_payload(gateway=gateway, url=url, node_type="section", node_id=node_id, parameters=parameters, prompt=prompt)
    _validate_report_fragment(REPORT_SECTION_FRAGMENT_VALIDATOR, payload, "custom section")
    return report_section_from_dict(payload)


def _fetch_custom_payload(
    *,
    gateway,
    url: str,
    node_type: str,
    node_id: str,
    parameters: dict[str, list[dict[str, Any]]],
    prompt: str,
) -> dict[str, Any]:
    if gateway is None:
        raise ValidationError("custom dynamic content gateway is not configured")
    if not url:
        raise ValidationError(f"custom dynamic {node_type} {node_id} missing url")
    request_payload = {
        "nodeType": node_type,
        "nodeId": node_id,
        "parameters": parameters,
        "prompt": prompt,
    }
    try:
        response = gateway.post_json(url=url, payload=request_payload)
    except Exception as exc:
        raise ValidationError(f"custom dynamic {node_type} {node_id} request failed: {exc}") from exc
    if not isinstance(response, dict):
        raise ValidationError(f"custom dynamic {node_type} {node_id} response must be a JSON object")
    return response


def _validate_report_fragment(validator: Draft202012Validator, payload: dict[str, Any], label: str) -> None:
    errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
    if not errors:
        return
    error = errors[0]
    path = ".".join(str(part) for part in error.absolute_path)
    prefix = f"{label} DSL 校验失败"
    if path:
        raise ValidationError(f"{prefix}: {path} {error.message}")
    raise ValidationError(f"{prefix}: {error.message}")


def _record_custom_catalog_meta(catalog: ReportCatalog, report_meta: dict[str, ReportGenerateMeta], *, prompt: str) -> None:
    for section in list(catalog.sections or []):
        report_meta[section.id] = ReportGenerateMeta(status="Success", question=prompt, additional_infos=[])
    for sub_catalog in list(catalog.sub_catalogs or []):
        _record_custom_catalog_meta(sub_catalog, report_meta, prompt=prompt)


def _build_section_components(section) -> tuple[list[Any], str, list[ReportAdditionalInfo]]:
    requirement_text = str(section.outline.rendered_requirement or section.outline.requirement or "")
    additional_infos: list[ReportAdditionalInfo] = []
    for binding in list(section.runtime_context.bindings or []):
        resolved_query = str(binding.resolved_query or "").strip()
        if resolved_query:
            additional_infos.append(ReportAdditionalInfo(type="SQL", value=resolved_query))

    # 当前运行时保持确定性生成：把正式诉求状态编译成文稿区块，
    # 并把已解析的执行绑定作为证据写入附加信息。
    components = [
        MarkdownComponent(
            id=f"component_{section.id}_markdown",
            type="markdown",
            data_properties=MarkdownDataProperties(
                data_type="static",
                content=_build_markdown_content(section, requirement_text),
            ),
        )
    ]
    components.extend(_build_presentation_components(section))
    summary = requirement_text or str(section.id or "")
    return components, summary[:160], additional_infos


def _build_markdown_content(section, requirement_text: str) -> str:
    lines = [f"## {_section_title(section)}".strip(), "", requirement_text or "本章节基于模板诉求自动生成。", ""]
    items = section.outline.items or []
    if items:
        lines.append("### 诉求要素")
        lines.append("")
        for item in items:
            values = [str(value.label or value.value or "") for value in item.values or []]
            rendered = "、".join([value for value in values if value]) or "未设置"
            lines.append(f"- {item.label}: {rendered}")
        lines.append("")
    lines.append("### 生成说明")
    lines.append("")
    lines.append("当前实现按正式模板实例生成报告 DSL，并保留诉求文本与执行绑定证据。")
    return "\n".join(lines).strip()


def _section_title(section) -> str:
    rendered_requirement = str(section.outline.rendered_requirement or section.outline.requirement or "").strip()
    if not rendered_requirement:
        return str(section.id or "")
    return rendered_requirement[:80]


def _build_report_name(*, template: ReportTemplate, template_instance: TemplateInstance) -> str:
    first_values = []
    for parameter in template_instance.parameters:
        values = parameter.values or []
        if values:
            first_values.append(str(values[0].label or values[0].value or ""))
        if len(first_values) >= 2:
            break
    suffix = " ".join([value for value in first_values if value])
    if suffix:
        return f"{suffix} {template.name}".strip()
    return template.name


def _build_report_summary(catalogs: list[ReportCatalog]) -> str:
    section_titles = _collect_section_titles(catalogs)
    if not section_titles:
        return "报告已生成。"
    return f"报告已生成，共包含 {len(section_titles)} 个章节：{'、'.join(section_titles[:5])}"


def _build_presentation_components(section) -> list[Any]:
    blocks = list(section.content.presentation.blocks or [])
    components: list[Any] = []
    for block in blocks:
        block_type = str(block.type or "")
        if block_type == "composite_table":
            components.append(_build_composite_table_component(block))
        elif block_type == "text":
            components.append(_build_text_component(block))
        elif block_type == "table":
            components.append(_build_table_component(block))
        elif block_type == "chart":
            components.append(_build_chart_component(block))
    return components


def _build_text_component(block) -> TextComponent:
    return TextComponent(
        id=str(block.id or ""),
        type="text",
        data_properties=TextDataProperties(
            data_type="static",
            content=str(getattr(block, "content", None) or ""),
            title=str(block.title or ""),
        ),
    )


def _build_table_component(block) -> TableComponent:
    columns = _presentation_columns(getattr(block, "properties", None))
    data: list[dict[str, Any]] = []
    return TableComponent(
        id=str(block.id or ""),
        type="table",
        data_properties=TableDataProperties(
            data_type="datasource",
            source_id=str(block.dataset_id or ""),
            title=str(block.title or ""),
            columns=columns,
            merge_columns=_presentation_merge_columns(getattr(block, "properties", None)),
            merge_rows=_build_merge_rows(data=data, columns=columns, definitions=_presentation_merge_rows(getattr(block, "properties", None))),
            data=data,
        ),
    )


def _build_chart_component(block) -> ChartComponent:
    return ChartComponent(
        id=str(block.id or ""),
        type="chart",
        data_properties=ChartDataProperties(
            data_type="datasource",
            source_id=str(block.dataset_id or ""),
            title=str(block.title or ""),
        ),
    )


def _build_composite_table_component(block) -> CompositeTableComponent:
    return CompositeTableComponent(
        id=str(block.id or ""),
        type="compositeTable",
        tables=[_build_composite_table_part(block, part) for part in list(block.parts or [])],
        data_properties=CompositeTableDataProperties(
            data_type="static",
            title=str(block.title or ""),
        ),
    )


def _build_composite_table_part(block, part) -> TableComponent:
    if str(part.source_type or "") == "summary":
        rows = []
        for row in list((part.summary_spec.rows if part.summary_spec else []) or []):
            rows.append({"title": str(row.title or ""), "content": "待补充"})
        columns = _layout_columns(part.table_layout)
        return TableComponent(
            id=str(part.id or ""),
            type="table",
            data_properties=TableDataProperties(
                data_type="static",
                title=str(part.title or ""),
                columns=columns,
                merge_rows=_build_merge_rows(data=rows, columns=columns, definitions=_layout_merge_rows(part.table_layout)),
                data=rows,
            ),
        )
    columns = _layout_columns(part.table_layout)
    data: list[dict[str, Any]] = []
    return TableComponent(
        id=str(part.id or ""),
        type="table",
        data_properties=TableDataProperties(
            data_type="datasource",
            source_id=str(part.dataset_id or ""),
            title=str(part.title or ""),
            columns=columns,
            merge_columns=_layout_merge_columns(part.table_layout),
            merge_rows=_build_merge_rows(data=data, columns=columns, definitions=_layout_merge_rows(part.table_layout)),
            data=data,
        ),
    )


def _presentation_columns(properties) -> list[ReportColumn]:
    if properties is None:
        return []
    return _table_columns(getattr(properties, "columns", []))


def _layout_columns(table_layout) -> list[ReportColumn]:
    if table_layout is None:
        return []
    return _table_columns(getattr(table_layout, "columns", []))


def _table_columns(columns) -> list[ReportColumn]:
    return [
        ReportColumn(
            key=str(column.key or ""),
            title=str(column.title or ""),
            width=getattr(column, "width", None),
            align=getattr(column, "align", None),
        )
        for column in list(columns or [])
    ]


def _layout_merge_columns(table_layout):
    if table_layout is None:
        return []
    return list(table_layout.merge_columns or [])


def _presentation_merge_rows(properties):
    if properties is None:
        return []
    return list(properties.merge_rows or [])


def _layout_merge_rows(table_layout):
    if table_layout is None:
        return []
    return list(table_layout.merge_rows or [])


def _build_merge_rows(*, data: list[dict[str, Any]], columns: list[ReportColumn], definitions) -> list[MergeRowInfo]:
    if not data or not definitions:
        return []
    column_keys = {str(column.key or "") for column in columns if str(column.key or "")}
    configs: list[MergeRowInfo] = []
    for definition in definitions:
        column = str(getattr(definition, "column", "") or "")
        if not column or column not in column_keys:
            continue
        configs.extend(_build_default_merge_rows(data=data, column=column))
    return configs


def _build_default_merge_rows(*, data: list[dict[str, Any]], column: str) -> list[MergeRowInfo]:
    configs: list[MergeRowInfo] = []
    start_index = 0
    while start_index < len(data):
        current_value = data[start_index].get(column)
        end_index = start_index + 1
        while end_index < len(data) and data[end_index].get(column) == current_value:
            end_index += 1
        row_span = end_index - start_index
        if row_span > 1:
            configs.append(
                MergeRowInfo(
                    start_row_index=start_index,
                    row_span=row_span,
                    column=column,
                    merged_text="" if current_value is None else str(current_value),
                )
            )
        start_index = end_index
    return configs


def _presentation_merge_columns(properties):
    if properties is None:
        return []
    return list(properties.merge_columns or [])


def _collect_section_titles(catalogs: list[ReportCatalog]) -> list[str]:
    titles: list[str] = []
    for catalog in catalogs:
        for section in list(catalog.sections or []):
            title = str(section.title or "").strip()
            if title:
                titles.append(title)
        titles.extend(_collect_section_titles(list(catalog.sub_catalogs or [])))
    return titles


def _count_catalogs(catalogs: list[ReportCatalog]) -> int:
    total = 0
    for catalog in catalogs:
        total += 1
        total += _count_catalogs(list(catalog.sub_catalogs or []))
    return total


def _resource_status_from_dsl(report: ReportDsl) -> str:
    status = str(report.basic_info.status or "").strip()
    if status == "Running":
        return "generating"
    if status == "Failed":
        return "failed"
    return "available"


def _build_generation_progress(report: ReportDsl) -> GenerationProgressView:
    total_sections = len(_collect_section_titles(list(report.catalogs or [])))
    total_catalogs = _count_catalogs(list(report.catalogs or []))
    return GenerationProgressView(
        total_sections=total_sections,
        completed_sections=total_sections,
        total_catalogs=total_catalogs,
        completed_catalogs=total_catalogs,
    )


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
