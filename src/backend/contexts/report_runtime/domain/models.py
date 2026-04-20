"""报告运行时聚合的 dataclass 定义：模板实例、报告实例与报告 DSL。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ....shared.kernel.dataclass_aliases import get_alias, get_value, set_value
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


def _alias_field(alias: str, **kwargs: Any):
    """为运行时 dataclass 字段声明公开 JSON 别名。"""

    metadata = dict(kwargs.pop("metadata", {}))
    metadata["alias"] = alias
    return field(metadata=metadata, **kwargs)


@dataclass(slots=True)
class ParameterConfirmation:
    """模板实例参数确认状态。"""

    missing_parameter_ids: list[str] = _alias_field("missingParameterIds", default_factory=list)
    confirmed: bool = False
    confirmed_at: str | None = _alias_field("confirmedAt", default=None)


@dataclass(slots=True)
class ForeachContext:
    """实例态 foreach 展开上下文。"""

    parameter_id: str = _alias_field("parameterId")
    item_values: list[ParameterValue] = _alias_field("itemValues", default_factory=list)


@dataclass(slots=True)
class ExecutionBinding:
    """章节执行绑定。"""

    id: str
    binding_type: str = _alias_field("bindingType")
    source_type: str = _alias_field("sourceType")
    target_ref: str = _alias_field("targetRef")
    multi_value_query_mode: str | None = _alias_field("multiValueQueryMode", default=None)
    query_template: str | None = _alias_field("queryTemplate", default=None)
    resolved_query: str | None = _alias_field("resolvedQuery", default=None)
    notes: str | None = None


@dataclass(slots=True)
class WarningItem:
    """运行时告警。"""

    code: str
    message: str
    target_id: str | None = _alias_field("targetId", default=None)


@dataclass(slots=True)
class PartRuntimeContext:
    """复合表分片运行时上下文。"""

    status: str
    resolved_dataset_id: str | None = _alias_field("resolvedDatasetId", default=None)
    resolved_query: str | None = _alias_field("resolvedQuery", default=None)
    resolved_part_ids: list[str] = _alias_field("resolvedPartIds", default_factory=list)
    prompt: str | None = None
    warnings: list[WarningItem] = field(default_factory=list)


@dataclass(slots=True)
class TemplateInstanceCompositeTablePart:
    """实例态复合表分片。"""

    id: str
    title: str
    source_type: str = _alias_field("sourceType")
    runtime_context: PartRuntimeContext = _alias_field("runtimeContext")
    description: str | None = None
    dataset_id: str | None = _alias_field("datasetId", default=None)
    summary_spec: SummaryTableSpec | None = _alias_field("summarySpec", default=None)
    table_layout: CompositeTablePartLayout | None = _alias_field("tableLayout", default=None)


@dataclass(slots=True)
class TemplateInstancePresentationBlock:
    """实例态展示块。"""

    id: str
    type: str
    title: str | None = None
    dataset_id: str | None = _alias_field("datasetId", default=None)
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
    runtime_context: SectionRuntimeContext = _alias_field("runtimeContext")
    skeleton_status: str = _alias_field("skeletonStatus")
    user_edited: bool = _alias_field("userEdited")
    description: str | None = None
    order: int | None = None
    parameters: list[Parameter] = field(default_factory=list)
    foreach_context: ForeachContext | None = _alias_field("foreachContext", default=None)


@dataclass(slots=True)
class TemplateInstanceCatalog:
    """实例态目录。"""

    id: str
    title: str
    rendered_title: str = _alias_field("renderedTitle")
    description: str | None = None
    order: int | None = None
    parameters: list[Parameter] = field(default_factory=list)
    foreach_context: ForeachContext | None = _alias_field("foreachContext", default=None)
    sub_catalogs: list["TemplateInstanceCatalog"] = _alias_field("subCatalogs", default_factory=list)
    sections: list[TemplateInstanceSection] = field(default_factory=list)


@dataclass(slots=True)
class TemplateInstance:
    """运行时聚合，持续维护一条报告对话对应的模板实例状态。"""

    id: str
    schema_version: str = _alias_field("schemaVersion")
    template_id: str = _alias_field("templateId")
    template: ReportTemplate
    conversation_id: str = _alias_field("conversationId")
    chat_id: str | None = _alias_field("chatId")
    status: str
    capture_stage: str = _alias_field("captureStage")
    revision: int
    parameters: list[Parameter] = field(default_factory=list)
    parameter_confirmation: ParameterConfirmation = _alias_field("parameterConfirmation", default_factory=ParameterConfirmation)
    catalogs: list[TemplateInstanceCatalog] = field(default_factory=list)
    warnings: list[WarningItem] = field(default_factory=list)
    created_at: datetime | None = _alias_field("createdAt", default=None)
    updated_at: datetime | None = _alias_field("updatedAt", default=None)


@dataclass(slots=True)
class ReportBasicInfo:
    """报告 DSL 基础信息。"""

    id: str
    schema_version: str = _alias_field("schemaVersion")
    mode: str
    status: str
    name: str | None = None
    sub_title: str | None = _alias_field("subTitle", default=None)
    description: str | None = None
    template_id: str | None = _alias_field("templateId", default=None)
    template_name: str | None = _alias_field("templateName", default=None)
    version: str | None = None
    create_date: str | None = _alias_field("createDate", default=None)
    modify_date: str | None = _alias_field("modifyDate", default=None)
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
    additional_infos: list[ReportAdditionalInfo] = _alias_field("additionalInfos", default_factory=list)


@dataclass(slots=True)
class GridDefinition:
    """页面网格。"""

    cols: int
    row_height: int = _alias_field("rowHeight")
    gap: int | None = None


@dataclass(slots=True)
class ReportLayout:
    """页面布局。"""

    type: str
    grid: GridDefinition | None = None


@dataclass(slots=True)
class MarkdownDataProperties:
    """Markdown 组件数据属性。"""

    data_type: str = _alias_field("dataType")
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

    data_type: str = _alias_field("dataType")
    source_id: str | None = _alias_field("sourceId", default=None)
    title: str | None = None
    columns: list[ReportColumn] = field(default_factory=list)
    data: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class CompositeTableDataProperties:
    """复合表组件数据属性。"""

    data_type: str = _alias_field("dataType")
    title: str | None = None


@dataclass(slots=True)
class MarkdownComponent:
    """Markdown 组件。"""

    id: str
    type: str
    data_properties: MarkdownDataProperties = _alias_field("dataProperties")


@dataclass(slots=True)
class TableComponent:
    """表格组件。"""

    id: str
    type: str
    data_properties: TableDataProperties = _alias_field("dataProperties")


@dataclass(slots=True)
class CompositeTableComponent:
    """复合表组件。"""

    id: str
    type: str
    tables: list[TableComponent] = field(default_factory=list)
    data_properties: CompositeTableDataProperties = _alias_field(
        "dataProperties", default_factory=lambda: CompositeTableDataProperties(data_type="static")
    )


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
    sub_catalogs: list["ReportCatalog"] = _alias_field("subCatalogs", default_factory=list)
    sections: list[ReportSection] = field(default_factory=list)


@dataclass(slots=True)
class ReportDsl:
    """正式报告 DSL 聚合。"""

    basic_info: ReportBasicInfo = _alias_field("basicInfo")
    catalogs: list[ReportCatalog] = field(default_factory=list)
    layout: ReportLayout = field(default_factory=lambda: ReportLayout(type="grid"))
    summary: ReportSummary | None = None
    report_meta: dict[str, ReportGenerateMeta] = _alias_field("reportMeta", default_factory=dict)


@dataclass(slots=True)
class ReportInstance:
    """冻结后的报告资源，内部承载最终报告结构。"""

    id: str
    template_id: str = _alias_field("templateId")
    template_instance_id: str = _alias_field("templateInstanceId")
    user_id: str = _alias_field("userId")
    source_conversation_id: str | None = _alias_field("sourceConversationId")
    source_chat_id: str | None = _alias_field("sourceChatId")
    status: str
    schema_version: str = _alias_field("schemaVersion")
    report: ReportDsl
    created_at: datetime | None = _alias_field("createdAt", default=None)
    updated_at: datetime | None = _alias_field("updatedAt", default=None)


@dataclass(slots=True)
class DocumentArtifact:
    """报告作用域下的导出文件元数据。"""

    id: str
    report_instance_id: str = _alias_field("reportInstanceId")
    artifact_kind: str = _alias_field("artifactKind")
    source_format: str | None = _alias_field("sourceFormat")
    generation_mode: str = _alias_field("generationMode")
    mime_type: str = _alias_field("mimeType")
    storage_key: str = _alias_field("storageKey")
    status: str
    error_message: str | None = _alias_field("errorMessage", default=None)
    created_at: datetime | None = _alias_field("createdAt", default=None)
    updated_at: datetime | None = _alias_field("updatedAt", default=None)


@dataclass(slots=True)
class ExportJob:
    """文档导出流水线中单一格式的一次执行记录。"""

    id: str
    report_instance_id: str = _alias_field("reportInstanceId")
    current_format: str = _alias_field("currentFormat")
    status: str
    dependency_job_id: str | None = _alias_field("dependencyJobId", default=None)
    exporter_backend: str = _alias_field("exporterBackend", default="local")
    request_payload_hash: str = _alias_field("requestPayloadHash", default="")
    started_at: datetime | None = _alias_field("startedAt", default=None)
    finished_at: datetime | None = _alias_field("finishedAt", default=None)
    error_code: str | None = _alias_field("errorCode", default=None)
    error_message: str | None = _alias_field("errorMessage", default=None)


def template_instance_to_dict(instance: TemplateInstance) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, TemplateInstance, "id", instance.id)
    set_value(payload, TemplateInstance, "schema_version", instance.schema_version)
    set_value(payload, TemplateInstance, "template_id", instance.template_id)
    set_value(payload, TemplateInstance, "template", report_template_to_dict(instance.template))
    set_value(payload, TemplateInstance, "conversation_id", instance.conversation_id)
    set_value(payload, TemplateInstance, "chat_id", instance.chat_id)
    set_value(payload, TemplateInstance, "status", instance.status)
    set_value(payload, TemplateInstance, "capture_stage", instance.capture_stage)
    set_value(payload, TemplateInstance, "revision", instance.revision)
    set_value(payload, TemplateInstance, "parameters", [parameter_to_dict(item) for item in instance.parameters])
    set_value(payload, TemplateInstance, "parameter_confirmation", parameter_confirmation_to_dict(instance.parameter_confirmation))
    set_value(payload, TemplateInstance, "catalogs", [template_instance_catalog_to_dict(item) for item in instance.catalogs])
    set_value(payload, TemplateInstance, "warnings", [warning_item_to_dict(item) for item in instance.warnings])
    set_value(payload, TemplateInstance, "created_at", _isoformat(instance.created_at))
    set_value(payload, TemplateInstance, "updated_at", _isoformat(instance.updated_at))
    return payload


def template_instance_from_dict(payload: dict[str, Any]) -> TemplateInstance:
    return TemplateInstance(
        id=str(get_value(payload, TemplateInstance, "id") or ""),
        schema_version=str(get_value(payload, TemplateInstance, "schema_version") or ""),
        template_id=str(get_value(payload, TemplateInstance, "template_id") or ""),
        template=report_template_from_dict(get_value(payload, TemplateInstance, "template") or {}),
        conversation_id=str(get_value(payload, TemplateInstance, "conversation_id") or ""),
        chat_id=_as_optional_str(get_value(payload, TemplateInstance, "chat_id")),
        status=str(get_value(payload, TemplateInstance, "status") or ""),
        capture_stage=str(get_value(payload, TemplateInstance, "capture_stage") or ""),
        revision=int(get_value(payload, TemplateInstance, "revision") or 1),
        parameters=[parameter_from_dict(item) for item in list(get_value(payload, TemplateInstance, "parameters") or [])],
        parameter_confirmation=parameter_confirmation_from_dict(get_value(payload, TemplateInstance, "parameter_confirmation")),
        catalogs=[template_instance_catalog_from_dict(item) for item in list(get_value(payload, TemplateInstance, "catalogs") or [])],
        warnings=[warning_item_from_dict(item) for item in list(get_value(payload, TemplateInstance, "warnings") or [])],
        created_at=_as_datetime(get_value(payload, TemplateInstance, "created_at")),
        updated_at=_as_datetime(get_value(payload, TemplateInstance, "updated_at")),
    )


def parameter_confirmation_to_dict(item: ParameterConfirmation) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, ParameterConfirmation, "missing_parameter_ids", list(item.missing_parameter_ids))
    set_value(payload, ParameterConfirmation, "confirmed", item.confirmed)
    if item.confirmed_at is not None:
        set_value(payload, ParameterConfirmation, "confirmed_at", item.confirmed_at)
    return payload


def parameter_confirmation_from_dict(payload: Any) -> ParameterConfirmation:
    if not isinstance(payload, dict):
        return ParameterConfirmation()
    return ParameterConfirmation(
        missing_parameter_ids=[str(item) for item in list(get_value(payload, ParameterConfirmation, "missing_parameter_ids") or [])],
        confirmed=bool(get_value(payload, ParameterConfirmation, "confirmed")),
        confirmed_at=_as_optional_str(get_value(payload, ParameterConfirmation, "confirmed_at")),
    )


def foreach_context_to_dict(item: ForeachContext) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, ForeachContext, "parameter_id", item.parameter_id)
    set_value(payload, ForeachContext, "item_values", [parameter_value_to_dict(value) for value in item.item_values])
    return payload


def foreach_context_from_dict(payload: Any) -> ForeachContext | None:
    if not isinstance(payload, dict):
        return None
    return ForeachContext(
        parameter_id=str(get_value(payload, ForeachContext, "parameter_id") or ""),
        item_values=[parameter_value_from_dict(item) for item in list(get_value(payload, ForeachContext, "item_values") or [])],
    )


def execution_binding_to_dict(binding: ExecutionBinding) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, ExecutionBinding, "id", binding.id)
    set_value(payload, ExecutionBinding, "binding_type", binding.binding_type)
    set_value(payload, ExecutionBinding, "source_type", binding.source_type)
    set_value(payload, ExecutionBinding, "target_ref", binding.target_ref)
    if binding.multi_value_query_mode is not None:
        set_value(payload, ExecutionBinding, "multi_value_query_mode", binding.multi_value_query_mode)
    if binding.query_template is not None:
        set_value(payload, ExecutionBinding, "query_template", binding.query_template)
    if binding.resolved_query is not None:
        set_value(payload, ExecutionBinding, "resolved_query", binding.resolved_query)
    if binding.notes is not None:
        set_value(payload, ExecutionBinding, "notes", binding.notes)
    return payload


def execution_binding_from_dict(payload: dict[str, Any]) -> ExecutionBinding:
    return ExecutionBinding(
        id=str(get_value(payload, ExecutionBinding, "id") or ""),
        binding_type=str(get_value(payload, ExecutionBinding, "binding_type") or ""),
        source_type=str(get_value(payload, ExecutionBinding, "source_type") or ""),
        target_ref=str(get_value(payload, ExecutionBinding, "target_ref") or ""),
        multi_value_query_mode=_as_optional_str(get_value(payload, ExecutionBinding, "multi_value_query_mode")),
        query_template=_as_optional_str(get_value(payload, ExecutionBinding, "query_template")),
        resolved_query=_as_optional_str(get_value(payload, ExecutionBinding, "resolved_query")),
        notes=_as_optional_str(get_value(payload, ExecutionBinding, "notes")),
    )


def warning_item_to_dict(item: WarningItem) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, WarningItem, "code", item.code)
    set_value(payload, WarningItem, "message", item.message)
    if item.target_id is not None:
        set_value(payload, WarningItem, "target_id", item.target_id)
    return payload


def warning_item_from_dict(payload: dict[str, Any]) -> WarningItem:
    return WarningItem(
        code=str(get_value(payload, WarningItem, "code") or ""),
        message=str(get_value(payload, WarningItem, "message") or ""),
        target_id=_as_optional_str(get_value(payload, WarningItem, "target_id")),
    )


def part_runtime_context_to_dict(context: PartRuntimeContext) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, PartRuntimeContext, "status", context.status)
    if context.resolved_dataset_id is not None:
        set_value(payload, PartRuntimeContext, "resolved_dataset_id", context.resolved_dataset_id)
    if context.resolved_query is not None:
        set_value(payload, PartRuntimeContext, "resolved_query", context.resolved_query)
    if context.resolved_part_ids:
        set_value(payload, PartRuntimeContext, "resolved_part_ids", list(context.resolved_part_ids))
    if context.prompt is not None:
        set_value(payload, PartRuntimeContext, "prompt", context.prompt)
    if context.warnings:
        set_value(payload, PartRuntimeContext, "warnings", [warning_item_to_dict(item) for item in context.warnings])
    return payload


def part_runtime_context_from_dict(payload: dict[str, Any]) -> PartRuntimeContext:
    return PartRuntimeContext(
        status=str(get_value(payload, PartRuntimeContext, "status") or ""),
        resolved_dataset_id=_as_optional_str(get_value(payload, PartRuntimeContext, "resolved_dataset_id")),
        resolved_query=_as_optional_str(get_value(payload, PartRuntimeContext, "resolved_query")),
        resolved_part_ids=[str(item) for item in list(get_value(payload, PartRuntimeContext, "resolved_part_ids") or [])],
        prompt=_as_optional_str(get_value(payload, PartRuntimeContext, "prompt")),
        warnings=[warning_item_from_dict(item) for item in list(get_value(payload, PartRuntimeContext, "warnings") or [])],
    )


def template_instance_composite_table_part_to_dict(part: TemplateInstanceCompositeTablePart) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, TemplateInstanceCompositeTablePart, "id", part.id)
    set_value(payload, TemplateInstanceCompositeTablePart, "title", part.title)
    set_value(payload, TemplateInstanceCompositeTablePart, "source_type", part.source_type)
    set_value(payload, TemplateInstanceCompositeTablePart, "runtime_context", part_runtime_context_to_dict(part.runtime_context))
    if part.description is not None:
        set_value(payload, TemplateInstanceCompositeTablePart, "description", part.description)
    if part.dataset_id is not None:
        set_value(payload, TemplateInstanceCompositeTablePart, "dataset_id", part.dataset_id)
    if part.summary_spec is not None:
        from ...template_catalog.domain.models import summary_table_spec_to_dict

        set_value(payload, TemplateInstanceCompositeTablePart, "summary_spec", summary_table_spec_to_dict(part.summary_spec))
    if part.table_layout is not None:
        from ...template_catalog.domain.models import composite_table_part_layout_to_dict

        set_value(payload, TemplateInstanceCompositeTablePart, "table_layout", composite_table_part_layout_to_dict(part.table_layout))
    return payload


def template_instance_composite_table_part_from_dict(payload: dict[str, Any]) -> TemplateInstanceCompositeTablePart:
    return TemplateInstanceCompositeTablePart(
        id=str(get_value(payload, TemplateInstanceCompositeTablePart, "id") or ""),
        title=str(get_value(payload, TemplateInstanceCompositeTablePart, "title") or ""),
        source_type=str(get_value(payload, TemplateInstanceCompositeTablePart, "source_type") or ""),
        runtime_context=part_runtime_context_from_dict(get_value(payload, TemplateInstanceCompositeTablePart, "runtime_context") or {}),
        description=_as_optional_str(get_value(payload, TemplateInstanceCompositeTablePart, "description")),
        dataset_id=_as_optional_str(get_value(payload, TemplateInstanceCompositeTablePart, "dataset_id")),
        summary_spec=_summary_spec_from_any(get_value(payload, TemplateInstanceCompositeTablePart, "summary_spec")),
        table_layout=_table_layout_from_any(get_value(payload, TemplateInstanceCompositeTablePart, "table_layout")),
    )


def template_instance_presentation_block_to_dict(block: TemplateInstancePresentationBlock) -> dict[str, Any]:
    payload: dict[str, Any] = {
        get_alias(TemplateInstancePresentationBlock, "id"): block.id,
        get_alias(TemplateInstancePresentationBlock, "type"): block.type,
    }
    if block.title is not None:
        set_value(payload, TemplateInstancePresentationBlock, "title", block.title)
    if block.dataset_id is not None:
        set_value(payload, TemplateInstancePresentationBlock, "dataset_id", block.dataset_id)
    if block.description is not None:
        set_value(payload, TemplateInstancePresentationBlock, "description", block.description)
    if block.parts:
        set_value(payload, TemplateInstancePresentationBlock, "parts", [template_instance_composite_table_part_to_dict(item) for item in block.parts])
    return payload


def template_instance_presentation_block_from_dict(payload: dict[str, Any]) -> TemplateInstancePresentationBlock:
    return TemplateInstancePresentationBlock(
        id=str(get_value(payload, TemplateInstancePresentationBlock, "id") or ""),
        type=str(get_value(payload, TemplateInstancePresentationBlock, "type") or ""),
        title=_as_optional_str(get_value(payload, TemplateInstancePresentationBlock, "title")),
        dataset_id=_as_optional_str(get_value(payload, TemplateInstancePresentationBlock, "dataset_id")),
        description=_as_optional_str(get_value(payload, TemplateInstancePresentationBlock, "description")),
        parts=[template_instance_composite_table_part_from_dict(item) for item in list(get_value(payload, TemplateInstancePresentationBlock, "parts") or [])],
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
    payload: dict[str, Any] = {}
    set_value(payload, SectionRuntimeContext, "bindings", [execution_binding_to_dict(item) for item in context.bindings])
    if context.notes is not None:
        set_value(payload, SectionRuntimeContext, "notes", context.notes)
    return payload


def section_runtime_context_from_dict(payload: dict[str, Any]) -> SectionRuntimeContext:
    return SectionRuntimeContext(
        bindings=[execution_binding_from_dict(item) for item in list(get_value(payload, SectionRuntimeContext, "bindings") or [])],
        notes=_as_optional_str(get_value(payload, SectionRuntimeContext, "notes")),
    )


def template_instance_section_to_dict(section: TemplateInstanceSection) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, TemplateInstanceSection, "id", section.id)
    set_value(payload, TemplateInstanceSection, "outline", outline_definition_to_dict(section.outline))
    set_value(payload, TemplateInstanceSection, "content", template_instance_section_content_to_dict(section.content))
    set_value(payload, TemplateInstanceSection, "runtime_context", section_runtime_context_to_dict(section.runtime_context))
    set_value(payload, TemplateInstanceSection, "skeleton_status", section.skeleton_status)
    set_value(payload, TemplateInstanceSection, "user_edited", section.user_edited)
    if section.description is not None:
        set_value(payload, TemplateInstanceSection, "description", section.description)
    if section.order is not None:
        set_value(payload, TemplateInstanceSection, "order", section.order)
    if section.parameters:
        set_value(payload, TemplateInstanceSection, "parameters", [parameter_to_dict(item) for item in section.parameters])
    if section.foreach_context is not None:
        set_value(payload, TemplateInstanceSection, "foreach_context", foreach_context_to_dict(section.foreach_context))
    return payload


def template_instance_section_from_dict(payload: dict[str, Any]) -> TemplateInstanceSection:
    return TemplateInstanceSection(
        id=str(get_value(payload, TemplateInstanceSection, "id") or ""),
        outline=_outline_from_any(get_value(payload, TemplateInstanceSection, "outline")),
        content=template_instance_section_content_from_dict(get_value(payload, TemplateInstanceSection, "content") or {}),
        runtime_context=section_runtime_context_from_dict(get_value(payload, TemplateInstanceSection, "runtime_context") or {}),
        skeleton_status=str(get_value(payload, TemplateInstanceSection, "skeleton_status") or ""),
        user_edited=bool(get_value(payload, TemplateInstanceSection, "user_edited")),
        description=_as_optional_str(get_value(payload, TemplateInstanceSection, "description")),
        order=_as_optional_int(get_value(payload, TemplateInstanceSection, "order")),
        parameters=[parameter_from_dict(item) for item in list(get_value(payload, TemplateInstanceSection, "parameters") or [])],
        foreach_context=foreach_context_from_dict(get_value(payload, TemplateInstanceSection, "foreach_context")),
    )


def template_instance_catalog_to_dict(catalog: TemplateInstanceCatalog) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, TemplateInstanceCatalog, "id", catalog.id)
    set_value(payload, TemplateInstanceCatalog, "title", catalog.title)
    set_value(payload, TemplateInstanceCatalog, "rendered_title", catalog.rendered_title)
    if catalog.description is not None:
        set_value(payload, TemplateInstanceCatalog, "description", catalog.description)
    if catalog.order is not None:
        set_value(payload, TemplateInstanceCatalog, "order", catalog.order)
    if catalog.parameters:
        set_value(payload, TemplateInstanceCatalog, "parameters", [parameter_to_dict(item) for item in catalog.parameters])
    if catalog.foreach_context is not None:
        set_value(payload, TemplateInstanceCatalog, "foreach_context", foreach_context_to_dict(catalog.foreach_context))
    if catalog.sub_catalogs:
        set_value(payload, TemplateInstanceCatalog, "sub_catalogs", [template_instance_catalog_to_dict(item) for item in catalog.sub_catalogs])
    if catalog.sections:
        set_value(payload, TemplateInstanceCatalog, "sections", [template_instance_section_to_dict(item) for item in catalog.sections])
    return payload


def template_instance_catalog_from_dict(payload: dict[str, Any]) -> TemplateInstanceCatalog:
    return TemplateInstanceCatalog(
        id=str(get_value(payload, TemplateInstanceCatalog, "id") or ""),
        title=str(get_value(payload, TemplateInstanceCatalog, "title") or ""),
        rendered_title=str(get_value(payload, TemplateInstanceCatalog, "rendered_title") or ""),
        description=_as_optional_str(get_value(payload, TemplateInstanceCatalog, "description")),
        order=_as_optional_int(get_value(payload, TemplateInstanceCatalog, "order")),
        parameters=[parameter_from_dict(item) for item in list(get_value(payload, TemplateInstanceCatalog, "parameters") or [])],
        foreach_context=foreach_context_from_dict(get_value(payload, TemplateInstanceCatalog, "foreach_context")),
        sub_catalogs=[template_instance_catalog_from_dict(item) for item in list(get_value(payload, TemplateInstanceCatalog, "sub_catalogs") or [])],
        sections=[template_instance_section_from_dict(item) for item in list(get_value(payload, TemplateInstanceCatalog, "sections") or [])],
    )


def report_dsl_to_dict(report: ReportDsl) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, ReportDsl, "basic_info", report_basic_info_to_dict(report.basic_info))
    set_value(payload, ReportDsl, "catalogs", [report_catalog_to_dict(item) for item in report.catalogs])
    set_value(payload, ReportDsl, "layout", report_layout_to_dict(report.layout))
    if report.summary is not None:
        set_value(payload, ReportDsl, "summary", report_summary_to_dict(report.summary))
    if report.report_meta:
        set_value(payload, ReportDsl, "report_meta", {key: report_generate_meta_to_dict(value) for key, value in report.report_meta.items()})
    return payload


def report_dsl_from_dict(payload: dict[str, Any]) -> ReportDsl:
    return ReportDsl(
        basic_info=report_basic_info_from_dict(get_value(payload, ReportDsl, "basic_info") or {}),
        catalogs=[report_catalog_from_dict(item) for item in list(get_value(payload, ReportDsl, "catalogs") or [])],
        layout=report_layout_from_dict(get_value(payload, ReportDsl, "layout") or {}),
        summary=report_summary_from_dict(get_value(payload, ReportDsl, "summary")) if isinstance(get_value(payload, ReportDsl, "summary"), dict) else None,
        report_meta={
            str(key): report_generate_meta_from_dict(value)
            for key, value in dict(get_value(payload, ReportDsl, "report_meta") or {}).items()
            if isinstance(value, dict)
        },
    )


def report_basic_info_to_dict(info: ReportBasicInfo) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, ReportBasicInfo, "id", info.id)
    set_value(payload, ReportBasicInfo, "schema_version", info.schema_version)
    set_value(payload, ReportBasicInfo, "mode", info.mode)
    set_value(payload, ReportBasicInfo, "status", info.status)
    _set_if(payload, ReportBasicInfo, "name", info.name)
    _set_if(payload, ReportBasicInfo, "sub_title", info.sub_title)
    _set_if(payload, ReportBasicInfo, "description", info.description)
    _set_if(payload, ReportBasicInfo, "template_id", info.template_id)
    _set_if(payload, ReportBasicInfo, "template_name", info.template_name)
    _set_if(payload, ReportBasicInfo, "version", info.version)
    _set_if(payload, ReportBasicInfo, "create_date", info.create_date)
    _set_if(payload, ReportBasicInfo, "modify_date", info.modify_date)
    _set_if(payload, ReportBasicInfo, "creator", info.creator)
    _set_if(payload, ReportBasicInfo, "modifier", info.modifier)
    _set_if(payload, ReportBasicInfo, "category", info.category)
    return payload


def report_basic_info_from_dict(payload: dict[str, Any]) -> ReportBasicInfo:
    return ReportBasicInfo(
        id=str(get_value(payload, ReportBasicInfo, "id") or ""),
        schema_version=str(get_value(payload, ReportBasicInfo, "schema_version") or ""),
        mode=str(get_value(payload, ReportBasicInfo, "mode") or ""),
        status=str(get_value(payload, ReportBasicInfo, "status") or ""),
        name=_as_optional_str(get_value(payload, ReportBasicInfo, "name")),
        sub_title=_as_optional_str(get_value(payload, ReportBasicInfo, "sub_title")),
        description=_as_optional_str(get_value(payload, ReportBasicInfo, "description")),
        template_id=_as_optional_str(get_value(payload, ReportBasicInfo, "template_id")),
        template_name=_as_optional_str(get_value(payload, ReportBasicInfo, "template_name")),
        version=_as_optional_str(get_value(payload, ReportBasicInfo, "version")),
        create_date=_as_optional_str(get_value(payload, ReportBasicInfo, "create_date")),
        modify_date=_as_optional_str(get_value(payload, ReportBasicInfo, "modify_date")),
        creator=_as_optional_str(get_value(payload, ReportBasicInfo, "creator")),
        modifier=_as_optional_str(get_value(payload, ReportBasicInfo, "modifier")),
        category=_as_optional_str(get_value(payload, ReportBasicInfo, "category")),
    )


def report_summary_to_dict(summary: ReportSummary) -> dict[str, Any]:
    return {"id": summary.id, "overview": summary.overview}


def report_summary_from_dict(payload: dict[str, Any]) -> ReportSummary:
    return ReportSummary(id=str(payload.get("id") or ""), overview=str(payload.get("overview") or ""))


def report_additional_info_to_dict(item: ReportAdditionalInfo) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, ReportAdditionalInfo, "type", item.type)
    set_value(payload, ReportAdditionalInfo, "value", item.value)
    _set_if(payload, ReportAdditionalInfo, "name", item.name)
    _set_if(payload, ReportAdditionalInfo, "appendix", item.appendix)
    return payload


def report_additional_info_from_dict(payload: dict[str, Any]) -> ReportAdditionalInfo:
    return ReportAdditionalInfo(
        type=str(payload.get("type") or ""),
        value=str(payload.get("value") or ""),
        name=_as_optional_str(payload.get("name")),
        appendix=_as_optional_str(payload.get("appendix")),
    )


def report_generate_meta_to_dict(meta: ReportGenerateMeta) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, ReportGenerateMeta, "status", meta.status)
    set_value(payload, ReportGenerateMeta, "question", meta.question)
    if meta.additional_infos:
        set_value(payload, ReportGenerateMeta, "additional_infos", [report_additional_info_to_dict(item) for item in meta.additional_infos])
    return payload


def report_generate_meta_from_dict(payload: dict[str, Any]) -> ReportGenerateMeta:
    return ReportGenerateMeta(
        status=str(get_value(payload, ReportGenerateMeta, "status") or ""),
        question=str(get_value(payload, ReportGenerateMeta, "question") or ""),
        additional_infos=[report_additional_info_from_dict(item) for item in list(get_value(payload, ReportGenerateMeta, "additional_infos") or [])],
    )


def report_layout_to_dict(layout: ReportLayout) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, ReportLayout, "type", layout.type)
    if layout.grid is not None:
        grid = {"cols": layout.grid.cols, get_alias(GridDefinition, "row_height"): layout.grid.row_height}
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
            row_height=int(grid_payload.get(get_alias(GridDefinition, "row_height")) or 0),
            gap=_as_optional_int(grid_payload.get("gap")),
        )
    return ReportLayout(type=str(get_value(payload, ReportLayout, "type") or ""), grid=grid)


def report_column_to_dict(column: ReportColumn) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, ReportColumn, "key", column.key)
    set_value(payload, ReportColumn, "title", column.title)
    _set_if(payload, ReportColumn, "width", column.width)
    _set_if(payload, ReportColumn, "align", column.align)
    if column.children:
        set_value(payload, ReportColumn, "children", [report_column_to_dict(item) for item in column.children])
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
        get_alias(MarkdownComponent, "id"): component.id,
        get_alias(MarkdownComponent, "type"): component.type,
        get_alias(MarkdownComponent, "data_properties"): {
            get_alias(MarkdownDataProperties, "data_type"): component.data_properties.data_type,
            "content": component.data_properties.content,
        },
    }


def markdown_component_from_dict(payload: dict[str, Any]) -> MarkdownComponent:
    data = get_value(payload, MarkdownComponent, "data_properties") if isinstance(get_value(payload, MarkdownComponent, "data_properties"), dict) else {}
    return MarkdownComponent(
        id=str(get_value(payload, MarkdownComponent, "id") or ""),
        type=str(get_value(payload, MarkdownComponent, "type") or ""),
        data_properties=MarkdownDataProperties(
            data_type=str(data.get(get_alias(MarkdownDataProperties, "data_type")) or ""),
            content=str(data.get("content") or ""),
        ),
    )


def table_component_to_dict(component: TableComponent) -> dict[str, Any]:
    payload = {
        get_alias(TableComponent, "id"): component.id,
        get_alias(TableComponent, "type"): component.type,
        get_alias(TableComponent, "data_properties"): {
            get_alias(TableDataProperties, "data_type"): component.data_properties.data_type,
        },
    }
    data_properties = payload[get_alias(TableComponent, "data_properties")]
    _set_if(data_properties, TableDataProperties, "source_id", component.data_properties.source_id)
    _set_if(data_properties, TableDataProperties, "title", component.data_properties.title)
    if component.data_properties.columns:
        data_properties["columns"] = [report_column_to_dict(item) for item in component.data_properties.columns]
    if component.data_properties.data:
        data_properties["data"] = list(component.data_properties.data)
    return payload


def table_component_from_dict(payload: dict[str, Any]) -> TableComponent:
    data = get_value(payload, TableComponent, "data_properties") if isinstance(get_value(payload, TableComponent, "data_properties"), dict) else {}
    return TableComponent(
        id=str(get_value(payload, TableComponent, "id") or ""),
        type=str(get_value(payload, TableComponent, "type") or ""),
        data_properties=TableDataProperties(
            data_type=str(data.get(get_alias(TableDataProperties, "data_type")) or ""),
            source_id=_as_optional_str(data.get(get_alias(TableDataProperties, "source_id"))),
            title=_as_optional_str(data.get(get_alias(TableDataProperties, "title"))),
            columns=[report_column_from_dict(item) for item in list(data.get("columns") or [])],
            data=list(data.get("data") or []),
        ),
    )


def composite_table_component_to_dict(component: CompositeTableComponent) -> dict[str, Any]:
    payload = {
        get_alias(CompositeTableComponent, "id"): component.id,
        get_alias(CompositeTableComponent, "type"): component.type,
        "tables": [table_component_to_dict(item) for item in component.tables],
    }
    payload[get_alias(CompositeTableComponent, "data_properties")] = {
        get_alias(CompositeTableDataProperties, "data_type"): component.data_properties.data_type,
    }
    _set_if(payload[get_alias(CompositeTableComponent, "data_properties")], CompositeTableDataProperties, "title", component.data_properties.title)
    return payload


def composite_table_component_from_dict(payload: dict[str, Any]) -> CompositeTableComponent:
    data = get_value(payload, CompositeTableComponent, "data_properties") if isinstance(get_value(payload, CompositeTableComponent, "data_properties"), dict) else {}
    return CompositeTableComponent(
        id=str(get_value(payload, CompositeTableComponent, "id") or ""),
        type=str(get_value(payload, CompositeTableComponent, "type") or ""),
        tables=[table_component_from_dict(item) for item in list(payload.get("tables") or [])],
        data_properties=CompositeTableDataProperties(
            data_type=str(data.get(get_alias(CompositeTableDataProperties, "data_type")) or ""),
            title=_as_optional_str(data.get(get_alias(CompositeTableDataProperties, "title"))),
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
    payload: dict[str, Any] = {}
    set_value(payload, ReportSection, "id", section.id)
    set_value(payload, ReportSection, "components", [report_component_to_dict(item) for item in section.components])
    _set_if(payload, ReportSection, "title", section.title)
    if section.order is not None:
        set_value(payload, ReportSection, "order", section.order)
    if section.summary is not None:
        set_value(payload, ReportSection, "summary", report_summary_to_dict(section.summary))
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
        get_alias(ReportCatalog, "id"): catalog.id,
        get_alias(ReportCatalog, "name"): catalog.name,
    }
    if catalog.order is not None:
        set_value(payload, ReportCatalog, "order", catalog.order)
    if catalog.sub_catalogs:
        set_value(payload, ReportCatalog, "sub_catalogs", [report_catalog_to_dict(item) for item in catalog.sub_catalogs])
    if catalog.sections:
        set_value(payload, ReportCatalog, "sections", [report_section_to_dict(item) for item in catalog.sections])
    return payload


def report_catalog_from_dict(payload: dict[str, Any]) -> ReportCatalog:
    return ReportCatalog(
        id=str(get_value(payload, ReportCatalog, "id") or ""),
        name=str(get_value(payload, ReportCatalog, "name") or ""),
        order=_as_optional_int(get_value(payload, ReportCatalog, "order")),
        sub_catalogs=[report_catalog_from_dict(item) for item in list(get_value(payload, ReportCatalog, "sub_catalogs") or [])],
        sections=[report_section_from_dict(item) for item in list(get_value(payload, ReportCatalog, "sections") or [])],
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


def _set_if(payload: dict[str, Any], model_type: type, field_name: str, value: Any) -> None:
    if value is not None:
        set_value(payload, model_type, field_name, value)


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
