"""报告运行时聚合的 dataclass 定义：模板实例、报告实例与报告 DSL。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ...template_catalog.domain.models import (
    CatalogDefinition,
    CompositeTableColumn,
    CompositeTablePart,
    CompositeTablePartLayout,
    DatasetDefinition,
    OutlineDefinition,
    Parameter,
    ParameterValue,
    ReportTemplate,
    SummaryTableSpec,
    catalog_definition_to_dict,
    outline_definition_to_dict,
    parameter_from_dict,
    parameter_to_dict,
    parameter_value_from_dict,
    parameter_value_to_dict,
    report_template_from_dict,
    report_template_to_dict,
)


@dataclass(slots=True)
class ParameterConfirmation:
    """模板实例参数确认状态。"""

    missing_parameter_ids: list[str] = field(default_factory=list)
    confirmed: bool = False
    confirmed_at: str | None = None


@dataclass(slots=True)
class ForeachContext:
    """实例态 foreach 展开上下文。"""

    parameter_id: str
    item_values: list[ParameterValue] = field(default_factory=list)


@dataclass(slots=True)
class ExecutionBinding:
    """章节执行绑定。"""

    id: str
    binding_type: str
    source_type: str
    target_ref: str
    multi_value_query_mode: str | None = None
    query_template: str | None = None
    resolved_query: str | None = None
    notes: str | None = None


@dataclass(slots=True)
class WarningItem:
    """运行时告警。"""

    code: str
    message: str
    target_id: str | None = None


@dataclass(slots=True)
class PartRuntimeContext:
    """复合表分片运行时上下文。"""

    status: str
    resolved_dataset_id: str | None = None
    resolved_query: str | None = None
    resolved_part_ids: list[str] = field(default_factory=list)
    prompt: str | None = None
    warnings: list[WarningItem] = field(default_factory=list)


@dataclass(slots=True)
class TemplateInstanceCompositeTablePart:
    """实例态复合表分片。"""

    id: str
    title: str
    source_type: str
    runtime_context: PartRuntimeContext
    description: str | None = None
    dataset_id: str | None = None
    summary_spec: SummaryTableSpec | None = None
    table_layout: CompositeTablePartLayout | None = None


@dataclass(slots=True)
class TemplateInstancePresentationBlock:
    """实例态展示块。"""

    id: str
    type: str
    title: str | None = None
    dataset_id: str | None = None
    description: str | None = None
    parts: list[TemplateInstanceCompositeTablePart] = field(default_factory=list)


@dataclass(slots=True)
class TemplateInstancePresentationDefinition:
    """实例态展示定义。"""

    kind: str
    blocks: list[TemplateInstancePresentationBlock] = field(default_factory=list)


@dataclass(slots=True)
class TemplateInstanceSectionContent:
    """实例态章节内容。"""

    presentation: TemplateInstancePresentationDefinition
    datasets: list[DatasetDefinition] = field(default_factory=list)


@dataclass(slots=True)
class SectionRuntimeContext:
    """章节运行时上下文。"""

    bindings: list[ExecutionBinding] = field(default_factory=list)
    notes: str | None = None


@dataclass(slots=True)
class TemplateInstanceSection:
    """实例态章节。"""

    id: str
    outline: OutlineDefinition
    content: TemplateInstanceSectionContent
    runtime_context: SectionRuntimeContext
    skeleton_status: str
    user_edited: bool
    description: str | None = None
    order: int | None = None
    parameters: list[Parameter] = field(default_factory=list)
    foreach_context: ForeachContext | None = None


@dataclass(slots=True)
class TemplateInstanceCatalog:
    """实例态目录。"""

    id: str
    title: str
    rendered_title: str
    description: str | None = None
    order: int | None = None
    parameters: list[Parameter] = field(default_factory=list)
    foreach_context: ForeachContext | None = None
    sub_catalogs: list["TemplateInstanceCatalog"] = field(default_factory=list)
    sections: list[TemplateInstanceSection] = field(default_factory=list)


@dataclass(slots=True)
class TemplateInstance:
    """运行时聚合，持续维护一条报告对话对应的模板实例状态。"""

    id: str
    schema_version: str
    template_id: str
    template: ReportTemplate
    conversation_id: str
    chat_id: str | None
    status: str
    capture_stage: str
    revision: int
    parameters: list[Parameter] = field(default_factory=list)
    parameter_confirmation: ParameterConfirmation = field(default_factory=ParameterConfirmation)
    catalogs: list[TemplateInstanceCatalog] = field(default_factory=list)
    warnings: list[WarningItem] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class ReportBasicInfo:
    """报告 DSL 基础信息。"""

    id: str
    schema_version: str
    mode: str
    status: str
    name: str | None = None
    sub_title: str | None = None
    description: str | None = None
    template_id: str | None = None
    template_name: str | None = None
    version: str | None = None
    create_date: str | None = None
    modify_date: str | None = None
    creator: str | None = None
    modifier: str | None = None
    category: str | None = None


@dataclass(slots=True)
class ReportSummary:
    """报告或章节摘要。"""

    id: str
    overview: str


@dataclass(slots=True)
class ReportAdditionalInfo:
    """报告生成附加信息。"""

    type: str
    value: str
    name: str | None = None
    appendix: str | None = None


@dataclass(slots=True)
class ReportGenerateMeta:
    """章节生成元信息。"""

    status: str
    question: str
    additional_infos: list[ReportAdditionalInfo] = field(default_factory=list)


@dataclass(slots=True)
class GridDefinition:
    """页面网格。"""

    cols: int
    row_height: int
    gap: int | None = None


@dataclass(slots=True)
class ReportLayout:
    """页面布局。"""

    type: str
    grid: GridDefinition | None = None


@dataclass(slots=True)
class MarkdownDataProperties:
    """Markdown 组件数据属性。"""

    data_type: str
    content: str


@dataclass(slots=True)
class ReportColumn:
    """表格列定义。"""

    key: str
    title: str
    width: str | None = None
    align: str | None = None
    children: list["ReportColumn"] = field(default_factory=list)


@dataclass(slots=True)
class TableDataProperties:
    """表格组件数据属性。"""

    data_type: str
    source_id: str | None = None
    title: str | None = None
    columns: list[ReportColumn] = field(default_factory=list)
    data: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class CompositeTableDataProperties:
    """复合表组件数据属性。"""

    data_type: str
    title: str | None = None


@dataclass(slots=True)
class MarkdownComponent:
    """Markdown 组件。"""

    id: str
    type: str
    data_properties: MarkdownDataProperties


@dataclass(slots=True)
class TableComponent:
    """表格组件。"""

    id: str
    type: str
    data_properties: TableDataProperties


@dataclass(slots=True)
class CompositeTableComponent:
    """复合表组件。"""

    id: str
    type: str
    tables: list[TableComponent] = field(default_factory=list)
    data_properties: CompositeTableDataProperties = field(default_factory=lambda: CompositeTableDataProperties(data_type="static"))


ReportComponent = MarkdownComponent | TableComponent | CompositeTableComponent


@dataclass(slots=True)
class ReportSection:
    """报告章节。"""

    id: str
    components: list[ReportComponent] = field(default_factory=list)
    title: str | None = None
    order: int | None = None
    summary: ReportSummary | None = None


@dataclass(slots=True)
class ReportCatalog:
    """报告目录。"""

    id: str
    name: str
    order: int | None = None
    sub_catalogs: list["ReportCatalog"] = field(default_factory=list)
    sections: list[ReportSection] = field(default_factory=list)


@dataclass(slots=True)
class ReportDsl:
    """正式报告 DSL 聚合。"""

    basic_info: ReportBasicInfo
    catalogs: list[ReportCatalog] = field(default_factory=list)
    layout: ReportLayout = field(default_factory=lambda: ReportLayout(type="grid"))
    summary: ReportSummary | None = None
    report_meta: dict[str, ReportGenerateMeta] = field(default_factory=dict)


@dataclass(slots=True)
class ReportInstance:
    """冻结后的报告资源，内部承载最终报告结构。"""

    id: str
    template_id: str
    template_instance_id: str
    user_id: str
    source_conversation_id: str | None
    source_chat_id: str | None
    status: str
    schema_version: str
    report: ReportDsl
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class DocumentArtifact:
    """报告作用域下的导出文件元数据。"""

    id: str
    report_instance_id: str
    artifact_kind: str
    source_format: str | None
    generation_mode: str
    mime_type: str
    storage_key: str
    status: str
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class ExportJob:
    """文档导出流水线中单一格式的一次执行记录。"""

    id: str
    report_instance_id: str
    current_format: str
    status: str
    dependency_job_id: str | None = None
    exporter_backend: str = "local"
    request_payload_hash: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None


def template_instance_to_dict(instance: TemplateInstance) -> dict[str, Any]:
    return {
        "id": instance.id,
        "schemaVersion": instance.schema_version,
        "templateId": instance.template_id,
        "template": report_template_to_dict(instance.template),
        "conversationId": instance.conversation_id,
        "chatId": instance.chat_id,
        "status": instance.status,
        "captureStage": instance.capture_stage,
        "revision": instance.revision,
        "parameters": [parameter_to_dict(item) for item in instance.parameters],
        "parameterConfirmation": parameter_confirmation_to_dict(instance.parameter_confirmation),
        "catalogs": [template_instance_catalog_to_dict(item) for item in instance.catalogs],
        "warnings": [warning_item_to_dict(item) for item in instance.warnings],
        "createdAt": _isoformat(instance.created_at),
        "updatedAt": _isoformat(instance.updated_at),
    }


def template_instance_from_dict(payload: dict[str, Any]) -> TemplateInstance:
    return TemplateInstance(
        id=str(payload.get("id") or ""),
        schema_version=str(payload.get("schemaVersion") or ""),
        template_id=str(payload.get("templateId") or ""),
        template=report_template_from_dict(payload.get("template") or {}),
        conversation_id=str(payload.get("conversationId") or ""),
        chat_id=_as_optional_str(payload.get("chatId")),
        status=str(payload.get("status") or ""),
        capture_stage=str(payload.get("captureStage") or ""),
        revision=int(payload.get("revision") or 1),
        parameters=[parameter_from_dict(item) for item in list(payload.get("parameters") or [])],
        parameter_confirmation=parameter_confirmation_from_dict(payload.get("parameterConfirmation")),
        catalogs=[template_instance_catalog_from_dict(item) for item in list(payload.get("catalogs") or [])],
        warnings=[warning_item_from_dict(item) for item in list(payload.get("warnings") or [])],
        created_at=_as_datetime(payload.get("createdAt")),
        updated_at=_as_datetime(payload.get("updatedAt")),
    )


def parameter_confirmation_to_dict(item: ParameterConfirmation) -> dict[str, Any]:
    payload = {
        "missingParameterIds": list(item.missing_parameter_ids),
        "confirmed": item.confirmed,
    }
    if item.confirmed_at is not None:
        payload["confirmedAt"] = item.confirmed_at
    return payload


def parameter_confirmation_from_dict(payload: Any) -> ParameterConfirmation:
    if not isinstance(payload, dict):
        return ParameterConfirmation()
    return ParameterConfirmation(
        missing_parameter_ids=[str(item) for item in list(payload.get("missingParameterIds") or [])],
        confirmed=bool(payload.get("confirmed")),
        confirmed_at=_as_optional_str(payload.get("confirmedAt")),
    )


def foreach_context_to_dict(item: ForeachContext) -> dict[str, Any]:
    return {
        "parameterId": item.parameter_id,
        "itemValues": [parameter_value_to_dict(value) for value in item.item_values],
    }


def foreach_context_from_dict(payload: Any) -> ForeachContext | None:
    if not isinstance(payload, dict):
        return None
    return ForeachContext(
        parameter_id=str(payload.get("parameterId") or ""),
        item_values=[parameter_value_from_dict(item) for item in list(payload.get("itemValues") or [])],
    )


def execution_binding_to_dict(binding: ExecutionBinding) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": binding.id,
        "bindingType": binding.binding_type,
        "sourceType": binding.source_type,
        "targetRef": binding.target_ref,
    }
    if binding.multi_value_query_mode is not None:
        payload["multiValueQueryMode"] = binding.multi_value_query_mode
    if binding.query_template is not None:
        payload["queryTemplate"] = binding.query_template
    if binding.resolved_query is not None:
        payload["resolvedQuery"] = binding.resolved_query
    if binding.notes is not None:
        payload["notes"] = binding.notes
    return payload


def execution_binding_from_dict(payload: dict[str, Any]) -> ExecutionBinding:
    return ExecutionBinding(
        id=str(payload.get("id") or ""),
        binding_type=str(payload.get("bindingType") or ""),
        source_type=str(payload.get("sourceType") or ""),
        target_ref=str(payload.get("targetRef") or ""),
        multi_value_query_mode=_as_optional_str(payload.get("multiValueQueryMode")),
        query_template=_as_optional_str(payload.get("queryTemplate")),
        resolved_query=_as_optional_str(payload.get("resolvedQuery")),
        notes=_as_optional_str(payload.get("notes")),
    )


def warning_item_to_dict(item: WarningItem) -> dict[str, Any]:
    payload = {
        "code": item.code,
        "message": item.message,
    }
    if item.target_id is not None:
        payload["targetId"] = item.target_id
    return payload


def warning_item_from_dict(payload: dict[str, Any]) -> WarningItem:
    return WarningItem(
        code=str(payload.get("code") or ""),
        message=str(payload.get("message") or ""),
        target_id=_as_optional_str(payload.get("targetId")),
    )


def part_runtime_context_to_dict(context: PartRuntimeContext) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": context.status,
    }
    if context.resolved_dataset_id is not None:
        payload["resolvedDatasetId"] = context.resolved_dataset_id
    if context.resolved_query is not None:
        payload["resolvedQuery"] = context.resolved_query
    if context.resolved_part_ids:
        payload["resolvedPartIds"] = list(context.resolved_part_ids)
    if context.prompt is not None:
        payload["prompt"] = context.prompt
    if context.warnings:
        payload["warnings"] = [warning_item_to_dict(item) for item in context.warnings]
    return payload


def part_runtime_context_from_dict(payload: dict[str, Any]) -> PartRuntimeContext:
    return PartRuntimeContext(
        status=str(payload.get("status") or ""),
        resolved_dataset_id=_as_optional_str(payload.get("resolvedDatasetId")),
        resolved_query=_as_optional_str(payload.get("resolvedQuery")),
        resolved_part_ids=[str(item) for item in list(payload.get("resolvedPartIds") or [])],
        prompt=_as_optional_str(payload.get("prompt")),
        warnings=[warning_item_from_dict(item) for item in list(payload.get("warnings") or [])],
    )


def template_instance_composite_table_part_to_dict(part: TemplateInstanceCompositeTablePart) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": part.id,
        "title": part.title,
        "sourceType": part.source_type,
        "runtimeContext": part_runtime_context_to_dict(part.runtime_context),
    }
    if part.description is not None:
        payload["description"] = part.description
    if part.dataset_id is not None:
        payload["datasetId"] = part.dataset_id
    if part.summary_spec is not None:
        from ...template_catalog.domain.models import summary_table_spec_to_dict

        payload["summarySpec"] = summary_table_spec_to_dict(part.summary_spec)
    if part.table_layout is not None:
        from ...template_catalog.domain.models import composite_table_part_layout_to_dict

        payload["tableLayout"] = composite_table_part_layout_to_dict(part.table_layout)
    return payload


def template_instance_composite_table_part_from_dict(payload: dict[str, Any]) -> TemplateInstanceCompositeTablePart:
    return TemplateInstanceCompositeTablePart(
        id=str(payload.get("id") or ""),
        title=str(payload.get("title") or ""),
        source_type=str(payload.get("sourceType") or ""),
        runtime_context=part_runtime_context_from_dict(payload.get("runtimeContext") or {}),
        description=_as_optional_str(payload.get("description")),
        dataset_id=_as_optional_str(payload.get("datasetId")),
        summary_spec=_summary_spec_from_any(payload.get("summarySpec")),
        table_layout=_table_layout_from_any(payload.get("tableLayout")),
    )


def template_instance_presentation_block_to_dict(block: TemplateInstancePresentationBlock) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": block.id,
        "type": block.type,
    }
    if block.title is not None:
        payload["title"] = block.title
    if block.dataset_id is not None:
        payload["datasetId"] = block.dataset_id
    if block.description is not None:
        payload["description"] = block.description
    if block.parts:
        payload["parts"] = [template_instance_composite_table_part_to_dict(item) for item in block.parts]
    return payload


def template_instance_presentation_block_from_dict(payload: dict[str, Any]) -> TemplateInstancePresentationBlock:
    return TemplateInstancePresentationBlock(
        id=str(payload.get("id") or ""),
        type=str(payload.get("type") or ""),
        title=_as_optional_str(payload.get("title")),
        dataset_id=_as_optional_str(payload.get("datasetId")),
        description=_as_optional_str(payload.get("description")),
        parts=[template_instance_composite_table_part_from_dict(item) for item in list(payload.get("parts") or [])],
    )


def template_instance_presentation_to_dict(presentation: TemplateInstancePresentationDefinition) -> dict[str, Any]:
    return {
        "kind": presentation.kind,
        "blocks": [template_instance_presentation_block_to_dict(item) for item in presentation.blocks],
    }


def template_instance_presentation_from_dict(payload: dict[str, Any]) -> TemplateInstancePresentationDefinition:
    return TemplateInstancePresentationDefinition(
        kind=str(payload.get("kind") or ""),
        blocks=[template_instance_presentation_block_from_dict(item) for item in list(payload.get("blocks") or [])],
    )


def template_instance_section_content_to_dict(content: TemplateInstanceSectionContent) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "presentation": template_instance_presentation_to_dict(content.presentation),
    }
    if content.datasets:
        from ...template_catalog.domain.models import dataset_definition_to_dict

        payload["datasets"] = [dataset_definition_to_dict(item) for item in content.datasets]
    return payload


def template_instance_section_content_from_dict(payload: dict[str, Any]) -> TemplateInstanceSectionContent:
    return TemplateInstanceSectionContent(
        presentation=template_instance_presentation_from_dict(payload.get("presentation") or {}),
        datasets=[_dataset_from_any(item) for item in list(payload.get("datasets") or [])],
    )


def section_runtime_context_to_dict(context: SectionRuntimeContext) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "bindings": [execution_binding_to_dict(item) for item in context.bindings],
    }
    if context.notes is not None:
        payload["notes"] = context.notes
    return payload


def section_runtime_context_from_dict(payload: dict[str, Any]) -> SectionRuntimeContext:
    return SectionRuntimeContext(
        bindings=[execution_binding_from_dict(item) for item in list(payload.get("bindings") or [])],
        notes=_as_optional_str(payload.get("notes")),
    )


def template_instance_section_to_dict(section: TemplateInstanceSection) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": section.id,
        "outline": outline_definition_to_dict(section.outline),
        "content": template_instance_section_content_to_dict(section.content),
        "runtimeContext": section_runtime_context_to_dict(section.runtime_context),
        "skeletonStatus": section.skeleton_status,
        "userEdited": section.user_edited,
    }
    if section.description is not None:
        payload["description"] = section.description
    if section.order is not None:
        payload["order"] = section.order
    if section.parameters:
        payload["parameters"] = [parameter_to_dict(item) for item in section.parameters]
    if section.foreach_context is not None:
        payload["foreachContext"] = foreach_context_to_dict(section.foreach_context)
    return payload


def template_instance_section_from_dict(payload: dict[str, Any]) -> TemplateInstanceSection:
    return TemplateInstanceSection(
        id=str(payload.get("id") or ""),
        outline=_outline_from_any(payload.get("outline")),
        content=template_instance_section_content_from_dict(payload.get("content") or {}),
        runtime_context=section_runtime_context_from_dict(payload.get("runtimeContext") or {}),
        skeleton_status=str(payload.get("skeletonStatus") or ""),
        user_edited=bool(payload.get("userEdited")),
        description=_as_optional_str(payload.get("description")),
        order=_as_optional_int(payload.get("order")),
        parameters=[parameter_from_dict(item) for item in list(payload.get("parameters") or [])],
        foreach_context=foreach_context_from_dict(payload.get("foreachContext")),
    )


def template_instance_catalog_to_dict(catalog: TemplateInstanceCatalog) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": catalog.id,
        "title": catalog.title,
        "renderedTitle": catalog.rendered_title,
    }
    if catalog.description is not None:
        payload["description"] = catalog.description
    if catalog.order is not None:
        payload["order"] = catalog.order
    if catalog.parameters:
        payload["parameters"] = [parameter_to_dict(item) for item in catalog.parameters]
    if catalog.foreach_context is not None:
        payload["foreachContext"] = foreach_context_to_dict(catalog.foreach_context)
    if catalog.sub_catalogs:
        payload["subCatalogs"] = [template_instance_catalog_to_dict(item) for item in catalog.sub_catalogs]
    if catalog.sections:
        payload["sections"] = [template_instance_section_to_dict(item) for item in catalog.sections]
    return payload


def template_instance_catalog_from_dict(payload: dict[str, Any]) -> TemplateInstanceCatalog:
    return TemplateInstanceCatalog(
        id=str(payload.get("id") or ""),
        title=str(payload.get("title") or ""),
        rendered_title=str(payload.get("renderedTitle") or ""),
        description=_as_optional_str(payload.get("description")),
        order=_as_optional_int(payload.get("order")),
        parameters=[parameter_from_dict(item) for item in list(payload.get("parameters") or [])],
        foreach_context=foreach_context_from_dict(payload.get("foreachContext")),
        sub_catalogs=[template_instance_catalog_from_dict(item) for item in list(payload.get("subCatalogs") or [])],
        sections=[template_instance_section_from_dict(item) for item in list(payload.get("sections") or [])],
    )


def report_dsl_to_dict(report: ReportDsl) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "basicInfo": report_basic_info_to_dict(report.basic_info),
        "catalogs": [report_catalog_to_dict(item) for item in report.catalogs],
        "layout": report_layout_to_dict(report.layout),
    }
    if report.summary is not None:
        payload["summary"] = report_summary_to_dict(report.summary)
    if report.report_meta:
        payload["reportMeta"] = {key: report_generate_meta_to_dict(value) for key, value in report.report_meta.items()}
    return payload


def report_dsl_from_dict(payload: dict[str, Any]) -> ReportDsl:
    return ReportDsl(
        basic_info=report_basic_info_from_dict(payload.get("basicInfo") or {}),
        catalogs=[report_catalog_from_dict(item) for item in list(payload.get("catalogs") or [])],
        layout=report_layout_from_dict(payload.get("layout") or {}),
        summary=report_summary_from_dict(payload.get("summary")) if isinstance(payload.get("summary"), dict) else None,
        report_meta={
            str(key): report_generate_meta_from_dict(value)
            for key, value in dict(payload.get("reportMeta") or {}).items()
            if isinstance(value, dict)
        },
    )


def report_basic_info_to_dict(info: ReportBasicInfo) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": info.id,
        "schemaVersion": info.schema_version,
        "mode": info.mode,
        "status": info.status,
    }
    _set_if(payload, "name", info.name)
    _set_if(payload, "subTitle", info.sub_title)
    _set_if(payload, "description", info.description)
    _set_if(payload, "templateId", info.template_id)
    _set_if(payload, "templateName", info.template_name)
    _set_if(payload, "version", info.version)
    _set_if(payload, "createDate", info.create_date)
    _set_if(payload, "modifyDate", info.modify_date)
    _set_if(payload, "creator", info.creator)
    _set_if(payload, "modifier", info.modifier)
    _set_if(payload, "category", info.category)
    return payload


def report_basic_info_from_dict(payload: dict[str, Any]) -> ReportBasicInfo:
    return ReportBasicInfo(
        id=str(payload.get("id") or ""),
        schema_version=str(payload.get("schemaVersion") or ""),
        mode=str(payload.get("mode") or ""),
        status=str(payload.get("status") or ""),
        name=_as_optional_str(payload.get("name")),
        sub_title=_as_optional_str(payload.get("subTitle")),
        description=_as_optional_str(payload.get("description")),
        template_id=_as_optional_str(payload.get("templateId")),
        template_name=_as_optional_str(payload.get("templateName")),
        version=_as_optional_str(payload.get("version")),
        create_date=_as_optional_str(payload.get("createDate")),
        modify_date=_as_optional_str(payload.get("modifyDate")),
        creator=_as_optional_str(payload.get("creator")),
        modifier=_as_optional_str(payload.get("modifier")),
        category=_as_optional_str(payload.get("category")),
    )


def report_summary_to_dict(summary: ReportSummary) -> dict[str, Any]:
    return {"id": summary.id, "overview": summary.overview}


def report_summary_from_dict(payload: dict[str, Any]) -> ReportSummary:
    return ReportSummary(id=str(payload.get("id") or ""), overview=str(payload.get("overview") or ""))


def report_additional_info_to_dict(item: ReportAdditionalInfo) -> dict[str, Any]:
    payload = {"type": item.type, "value": item.value}
    _set_if(payload, "name", item.name)
    _set_if(payload, "appendix", item.appendix)
    return payload


def report_additional_info_from_dict(payload: dict[str, Any]) -> ReportAdditionalInfo:
    return ReportAdditionalInfo(
        type=str(payload.get("type") or ""),
        value=str(payload.get("value") or ""),
        name=_as_optional_str(payload.get("name")),
        appendix=_as_optional_str(payload.get("appendix")),
    )


def report_generate_meta_to_dict(meta: ReportGenerateMeta) -> dict[str, Any]:
    payload = {"status": meta.status, "question": meta.question}
    if meta.additional_infos:
        payload["additionalInfos"] = [report_additional_info_to_dict(item) for item in meta.additional_infos]
    return payload


def report_generate_meta_from_dict(payload: dict[str, Any]) -> ReportGenerateMeta:
    return ReportGenerateMeta(
        status=str(payload.get("status") or ""),
        question=str(payload.get("question") or ""),
        additional_infos=[report_additional_info_from_dict(item) for item in list(payload.get("additionalInfos") or [])],
    )


def report_layout_to_dict(layout: ReportLayout) -> dict[str, Any]:
    payload = {"type": layout.type}
    if layout.grid is not None:
        grid = {"cols": layout.grid.cols, "rowHeight": layout.grid.row_height}
        if layout.grid.gap is not None:
            grid["gap"] = layout.grid.gap
        payload["grid"] = grid
    return payload


def report_layout_from_dict(payload: dict[str, Any]) -> ReportLayout:
    grid_payload = payload.get("grid") if isinstance(payload.get("grid"), dict) else None
    grid = None
    if grid_payload is not None:
        grid = GridDefinition(
            cols=int(grid_payload.get("cols") or 0),
            row_height=int(grid_payload.get("rowHeight") or 0),
            gap=_as_optional_int(grid_payload.get("gap")),
        )
    return ReportLayout(type=str(payload.get("type") or ""), grid=grid)


def report_column_to_dict(column: ReportColumn) -> dict[str, Any]:
    payload = {"key": column.key, "title": column.title}
    _set_if(payload, "width", column.width)
    _set_if(payload, "align", column.align)
    if column.children:
        payload["children"] = [report_column_to_dict(item) for item in column.children]
    return payload


def report_column_from_dict(payload: dict[str, Any]) -> ReportColumn:
    return ReportColumn(
        key=str(payload.get("key") or ""),
        title=str(payload.get("title") or ""),
        width=_as_optional_str(payload.get("width")),
        align=_as_optional_str(payload.get("align")),
        children=[report_column_from_dict(item) for item in list(payload.get("children") or [])],
    )


def markdown_component_to_dict(component: MarkdownComponent) -> dict[str, Any]:
    return {
        "id": component.id,
        "type": component.type,
        "dataProperties": {
            "dataType": component.data_properties.data_type,
            "content": component.data_properties.content,
        },
    }


def markdown_component_from_dict(payload: dict[str, Any]) -> MarkdownComponent:
    data = payload.get("dataProperties") if isinstance(payload.get("dataProperties"), dict) else {}
    return MarkdownComponent(
        id=str(payload.get("id") or ""),
        type=str(payload.get("type") or ""),
        data_properties=MarkdownDataProperties(
            data_type=str(data.get("dataType") or ""),
            content=str(data.get("content") or ""),
        ),
    )


def table_component_to_dict(component: TableComponent) -> dict[str, Any]:
    payload = {
        "id": component.id,
        "type": component.type,
        "dataProperties": {
            "dataType": component.data_properties.data_type,
        },
    }
    data_properties = payload["dataProperties"]
    _set_if(data_properties, "sourceId", component.data_properties.source_id)
    _set_if(data_properties, "title", component.data_properties.title)
    if component.data_properties.columns:
        data_properties["columns"] = [report_column_to_dict(item) for item in component.data_properties.columns]
    if component.data_properties.data:
        data_properties["data"] = list(component.data_properties.data)
    return payload


def table_component_from_dict(payload: dict[str, Any]) -> TableComponent:
    data = payload.get("dataProperties") if isinstance(payload.get("dataProperties"), dict) else {}
    return TableComponent(
        id=str(payload.get("id") or ""),
        type=str(payload.get("type") or ""),
        data_properties=TableDataProperties(
            data_type=str(data.get("dataType") or ""),
            source_id=_as_optional_str(data.get("sourceId")),
            title=_as_optional_str(data.get("title")),
            columns=[report_column_from_dict(item) for item in list(data.get("columns") or [])],
            data=list(data.get("data") or []),
        ),
    )


def composite_table_component_to_dict(component: CompositeTableComponent) -> dict[str, Any]:
    payload = {
        "id": component.id,
        "type": component.type,
        "tables": [table_component_to_dict(item) for item in component.tables],
    }
    payload["dataProperties"] = {
        "dataType": component.data_properties.data_type,
    }
    _set_if(payload["dataProperties"], "title", component.data_properties.title)
    return payload


def composite_table_component_from_dict(payload: dict[str, Any]) -> CompositeTableComponent:
    data = payload.get("dataProperties") if isinstance(payload.get("dataProperties"), dict) else {}
    return CompositeTableComponent(
        id=str(payload.get("id") or ""),
        type=str(payload.get("type") or ""),
        tables=[table_component_from_dict(item) for item in list(payload.get("tables") or [])],
        data_properties=CompositeTableDataProperties(
            data_type=str(data.get("dataType") or ""),
            title=_as_optional_str(data.get("title")),
        ),
    )


def report_component_to_dict(component: ReportComponent) -> dict[str, Any]:
    if isinstance(component, MarkdownComponent):
        return markdown_component_to_dict(component)
    if isinstance(component, TableComponent):
        return table_component_to_dict(component)
    return composite_table_component_to_dict(component)


def report_component_from_dict(payload: dict[str, Any]) -> ReportComponent:
    component_type = str(payload.get("type") or "")
    if component_type == "markdown":
        return markdown_component_from_dict(payload)
    if component_type == "table":
        return table_component_from_dict(payload)
    return composite_table_component_from_dict(payload)


def report_section_to_dict(section: ReportSection) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": section.id,
        "components": [report_component_to_dict(item) for item in section.components],
    }
    _set_if(payload, "title", section.title)
    if section.order is not None:
        payload["order"] = section.order
    if section.summary is not None:
        payload["summary"] = report_summary_to_dict(section.summary)
    return payload


def report_section_from_dict(payload: dict[str, Any]) -> ReportSection:
    return ReportSection(
        id=str(payload.get("id") or ""),
        title=_as_optional_str(payload.get("title")),
        order=_as_optional_int(payload.get("order")),
        components=[report_component_from_dict(item) for item in list(payload.get("components") or [])],
        summary=report_summary_from_dict(payload.get("summary")) if isinstance(payload.get("summary"), dict) else None,
    )


def report_catalog_to_dict(catalog: ReportCatalog) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": catalog.id,
        "name": catalog.name,
    }
    if catalog.order is not None:
        payload["order"] = catalog.order
    if catalog.sub_catalogs:
        payload["subCatalogs"] = [report_catalog_to_dict(item) for item in catalog.sub_catalogs]
    if catalog.sections:
        payload["sections"] = [report_section_to_dict(item) for item in catalog.sections]
    return payload


def report_catalog_from_dict(payload: dict[str, Any]) -> ReportCatalog:
    return ReportCatalog(
        id=str(payload.get("id") or ""),
        name=str(payload.get("name") or ""),
        order=_as_optional_int(payload.get("order")),
        sub_catalogs=[report_catalog_from_dict(item) for item in list(payload.get("subCatalogs") or [])],
        sections=[report_section_from_dict(item) for item in list(payload.get("sections") or [])],
    )


def _dataset_from_any(payload: Any) -> DatasetDefinition:
    if isinstance(payload, DatasetDefinition):
        return payload
    if isinstance(payload, dict):
        from ...template_catalog.domain.models import dataset_definition_from_dict

        return dataset_definition_from_dict(payload)
    return DatasetDefinition(id="", source_type="", source_ref="")


def _outline_from_any(payload: Any) -> OutlineDefinition:
    if isinstance(payload, OutlineDefinition):
        return payload
    if isinstance(payload, dict):
        from ...template_catalog.domain.models import outline_definition_from_dict

        return outline_definition_from_dict(payload)
    return OutlineDefinition(requirement="")


def _summary_spec_from_any(payload: Any) -> SummaryTableSpec | None:
    if isinstance(payload, SummaryTableSpec):
        return payload
    if isinstance(payload, dict):
        from ...template_catalog.domain.models import summary_table_spec_from_dict

        return summary_table_spec_from_dict(payload)
    return None


def _table_layout_from_any(payload: Any) -> CompositeTablePartLayout | None:
    if isinstance(payload, CompositeTablePartLayout):
        return payload
    if isinstance(payload, dict):
        from ...template_catalog.domain.models import composite_table_part_layout_from_dict

        return composite_table_part_layout_from_dict(payload)
    return None


def _set_if(payload: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        payload[key] = value


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def _as_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _as_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
