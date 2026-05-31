"""报告运行时聚合的 dataclass 定义：模板实例、报告实例与报告 DSL。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ....shared.kernel.dataclass_aliases import get_alias, get_value, set_value
from ...template_catalog.domain.models import (
    CatalogDefinition,
    CompositeTableColumn,
    MergeColumnInfo,
    MergeRowDefinition,
    CompositeTablePart,
    CompositeTablePartLayout,
    DatasetDefinition,
    OutlineDefinition,
    Parameter,
    ParameterValue,
    PresentationProperty,
    ReportTemplate,
    SlideLayout,
    SummaryTableSpec,
    catalog_definition_to_dict,
    outline_definition_to_dict,
    parameter_from_dict,
    parameter_to_dict,
    parameter_value_from_dict,
    parameter_value_to_dict,
    presentation_property_with_text,
    report_template_from_dict,
    report_template_to_dict,
    slide_layout_from_dict,
    slide_layout_to_dict,
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
class DynamicContext:
    """实例态 dynamic 展开上下文。"""

    type: str
    parameter_id: str | None = _alias_field("parameterId", default=None)
    item_value: ParameterValue | None = _alias_field("itemValue", default=None)
    case_id: str | None = _alias_field("caseId", default=None)
    url: str | None = None
    node_type: str | None = _alias_field("nodeType", default=None)


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


@dataclass(slots=True, init=False)
class TemplateInstancePresentationBlock:
    """实例态展示块。"""

    id: str
    type: str
    title: str | None = None
    dataset_id: str | None = _alias_field("datasetId", default=None)
    properties: PresentationProperty | None = None
    description: str | None = None
    parts: list[TemplateInstanceCompositeTablePart] = field(default_factory=list)

    def __init__(
        self,
        id: str,
        type: str,
        title: str | None = None,
        dataset_id: str | None = None,
        properties: PresentationProperty | None = None,
        template: str | None = None,
        content: str | None = None,
        description: str | None = None,
        parts: list[TemplateInstanceCompositeTablePart] | None = None,
    ) -> None:
        self.id = id
        self.type = type
        self.title = title
        self.dataset_id = dataset_id
        self.properties = presentation_property_with_text(properties, template=template, content=content)
        self.description = description
        self.parts = list(parts or [])

    @property
    def template(self) -> str | None:
        return self.properties.template if self.properties is not None else None

    @template.setter
    def template(self, value: str | None) -> None:
        self.properties = presentation_property_with_text(self.properties, template=value)

    @property
    def content(self) -> str | None:
        return self.properties.content if self.properties is not None else None

    @content.setter
    def content(self, value: str | None) -> None:
        self.properties = presentation_property_with_text(self.properties, content=value)


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
    dynamic_context: DynamicContext | None = _alias_field("dynamicContext", default=None)
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
    dynamic_context: DynamicContext | None = _alias_field("dynamicContext", default=None)
    foreach_context: ForeachContext | None = _alias_field("foreachContext", default=None)
    sub_catalogs: list["TemplateInstanceCatalog"] = _alias_field("subCatalogs", default_factory=list)
    sections: list[TemplateInstanceSection] = field(default_factory=list)


@dataclass(slots=True)
class TemplateInstanceSlide:
    """实例态分页页面。"""

    id: str
    title: str | None = None
    subtitle: str | None = None
    description: str | None = None
    order: int | None = None
    parameters: list[Parameter] = field(default_factory=list)
    dynamic_context: DynamicContext | None = _alias_field("dynamicContext", default=None)
    layout: SlideLayout | None = None
    sections: list[TemplateInstanceSection] = field(default_factory=list)


@dataclass(slots=True)
class TemplateInstanceChapter:
    """实例态分页章节。"""

    id: str
    title: str | None = None
    description: str | None = None
    implicit: bool | None = None
    order: int | None = None
    parameters: list[Parameter] = field(default_factory=list)
    dynamic_context: DynamicContext | None = _alias_field("dynamicContext", default=None)
    slides: list[TemplateInstanceSlide] = field(default_factory=list)


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
    structure_type: str = _alias_field("structureType", default="flow")
    parameters: list[Parameter] = field(default_factory=list)
    parameter_confirmation: ParameterConfirmation = _alias_field("parameterConfirmation", default_factory=ParameterConfirmation)
    catalogs: list[TemplateInstanceCatalog] = field(default_factory=list)
    chapters: list[TemplateInstanceChapter] = field(default_factory=list)
    warnings: list[WarningItem] = field(default_factory=list)
    created_at: datetime | None = _alias_field("createdAt", default=None)
    updated_at: datetime | None = _alias_field("updatedAt", default=None)


@dataclass(slots=True)
class ReportBasicInfo:
    """报告 DSL 基础信息。"""

    id: str
    asset_schema_version: str | None = _alias_field("schemaVersion", default=None)
    name: str | None = None
    report_type: str | None = _alias_field("reportType", default=None)
    description: str | None = None
    schema_version: str | None = _alias_field("version", default=None)
    status: str | None = None
    mode: str | None = None
    template_id: str | None = _alias_field("templateId", default=None)
    template_name: str | None = _alias_field("templateName", default=None)
    remark: str | None = None
    create_date: str | None = _alias_field("createDate", default=None)
    modify_date: str | None = _alias_field("modifyDate", default=None)
    creator: str | None = None
    modifier: str | None = None
    header: str | None = None
    footer: str | None = None
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
    outline: OutlineDefinition | None = None
    parameters: dict[str, Parameter] = field(default_factory=dict)


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
    auto_layout: bool | None = _alias_field("autoLayout", default=None)
    grid: GridDefinition | None = None


@dataclass(slots=True)
class MarkdownDataProperties:
    """Markdown 组件数据属性。"""

    data_type: str = _alias_field("dataType")
    content: str
    source_id: str | None = _alias_field("sourceId", default=None)
    url: str | None = None
    method: str | None = None
    auto_refresh: bool | None = _alias_field("autoRefresh", default=None)
    refresh_interval: float | None = _alias_field("refreshInterval", default=None)


@dataclass(slots=True)
class TextDataProperties:
    """文本组件数据属性。"""

    data_type: str = _alias_field("dataType")
    content: str
    source_id: str | None = _alias_field("sourceId", default=None)
    url: str | None = None
    method: str | None = None
    auto_refresh: bool | None = _alias_field("autoRefresh", default=None)
    refresh_interval: float | None = _alias_field("refreshInterval", default=None)
    title: str | None = None


@dataclass(slots=True)
class ReportColumn:
    """表格列定义。"""

    key: str
    title: str
    type: str | None = None
    width: str | int | float | None = None
    sortable: bool | None = None
    filterable: bool | None = None
    align: str | None = None
    children: list["ReportColumn"] = field(default_factory=list)


@dataclass(slots=True)
class TableDataProperties:
    """表格组件数据属性。"""

    data_type: str = _alias_field("dataType")
    source_id: str | None = _alias_field("sourceId", default=None)
    url: str | None = None
    method: str | None = None
    auto_refresh: bool | None = _alias_field("autoRefresh", default=None)
    refresh_interval: float | None = _alias_field("refreshInterval", default=None)
    title: str | None = None
    columns: list[ReportColumn] = field(default_factory=list)
    merge_columns: list[MergeColumnInfo] = _alias_field("mergeColumns", default_factory=list)
    merge_rows: list["MergeRowInfo"] = _alias_field("mergeRows", default_factory=list)
    data: list[dict[str, Any]] = field(default_factory=list)
    has_merge: bool | None = _alias_field("hasMerge", default=None)


@dataclass(slots=True)
class MergeRowInfo:
    """表格行合并渲染配置。"""

    start_row_index: int = _alias_field("startRowIndex")
    row_span: int = _alias_field("rowSpan")
    column: str
    merged_text: str | None = _alias_field("mergedText", default=None)


@dataclass(slots=True)
class ChartDataProperties:
    """图表组件数据属性。"""

    data_type: str = _alias_field("dataType")
    source_id: str | None = _alias_field("sourceId", default=None)
    url: str | None = None
    method: str | None = None
    auto_refresh: bool | None = _alias_field("autoRefresh", default=None)
    refresh_interval: float | None = _alias_field("refreshInterval", default=None)
    title: str | None = None
    columns: list[ReportColumn] = field(default_factory=list)
    data: list[dict[str, Any]] = field(default_factory=list)
    series: list[dict[str, Any]] = field(default_factory=list)
    axis_group: list[str] = _alias_field("axisGroup", default_factory=list)
    x_axis: dict[str, Any] | list[dict[str, Any]] | None = _alias_field("xAxis", default=None)
    y_axis: dict[str, Any] | list[dict[str, Any]] | None = _alias_field("yAxis", default=None)


@dataclass(slots=True)
class CompositeTableDataProperties:
    """复合表组件数据属性。"""

    data_type: str = _alias_field("dataType")
    source_id: str | None = _alias_field("sourceId", default=None)
    url: str | None = None
    method: str | None = None
    auto_refresh: bool | None = _alias_field("autoRefresh", default=None)
    refresh_interval: float | None = _alias_field("refreshInterval", default=None)
    title: str | None = None


@dataclass(slots=True)
class MarkdownComponent:
    """Markdown 组件。"""

    id: str
    type: str
    data_properties: MarkdownDataProperties = _alias_field("dataProperties")
    layout: dict[str, Any] | None = None
    basic_properties: dict[str, Any] | None = _alias_field("basicProperties", default=None)
    advance_properties: dict[str, Any] | None = _alias_field("advanceProperties", default=None)
    interactions: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class TextComponent:
    """文本组件。"""

    id: str
    type: str
    data_properties: TextDataProperties = _alias_field("dataProperties")
    layout: dict[str, Any] | None = None
    basic_properties: dict[str, Any] | None = _alias_field("basicProperties", default=None)
    advance_properties: dict[str, Any] | None = _alias_field("advanceProperties", default=None)
    interactions: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class TableComponent:
    """表格组件。"""

    id: str
    type: str
    data_properties: TableDataProperties = _alias_field("dataProperties")
    layout: dict[str, Any] | None = None
    basic_properties: dict[str, Any] | None = _alias_field("basicProperties", default=None)
    advance_properties: dict[str, Any] | None = _alias_field("advanceProperties", default=None)
    interactions: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class ChartComponent:
    """图表组件。"""

    id: str
    type: str
    data_properties: ChartDataProperties = _alias_field("dataProperties")
    layout: dict[str, Any] | None = None
    basic_properties: dict[str, Any] | None = _alias_field("basicProperties", default=None)
    advance_properties: dict[str, Any] | None = _alias_field("advanceProperties", default=None)
    interactions: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class CompositeTableComponent:
    """复合表组件。"""

    id: str
    type: str
    tables: list[TableComponent] = field(default_factory=list)
    data_properties: CompositeTableDataProperties = _alias_field(
        "dataProperties", default_factory=lambda: CompositeTableDataProperties(data_type="static")
    )
    layout: dict[str, Any] | None = None
    basic_properties: dict[str, Any] | None = _alias_field("basicProperties", default=None)
    advance_properties: dict[str, Any] | None = _alias_field("advanceProperties", default=None)
    interactions: list[dict[str, Any]] = field(default_factory=list)


ReportComponent = MarkdownComponent | TextComponent | TableComponent | ChartComponent | CompositeTableComponent


@dataclass(slots=True)
class ReportSection:
    """报告章节。"""

    id: str
    components: list[ReportComponent] = field(default_factory=list)
    title: str | None = None
    description: str | None = None
    layout: dict[str, Any] | None = None
    order: int | None = None
    summary: ReportSummary | None = None


@dataclass(slots=True)
class ReportCatalog:
    """报告目录。"""

    id: str
    name: str | None = None
    title: str | None = None
    description: str | None = None
    order: int | None = None
    sub_catalogs: list["ReportCatalog"] = _alias_field("subCatalogs", default_factory=list)
    sections: list[ReportSection] = field(default_factory=list)


@dataclass(slots=True)
class ReportCoverContent:
    """报告封面内容项。"""

    type: str
    content: str
    element_id: str = _alias_field("elementId")


@dataclass(slots=True)
class ReportCover:
    """报告封面。"""

    title: str
    author: str | None = None
    date: str | None = None
    layout_template: str | None = _alias_field("layoutTemplate", default=None)
    image: str | None = None
    contents: list[ReportCoverContent] = field(default_factory=list)


@dataclass(slots=True)
class ReportSigner:
    """报告签署人。"""

    name: str
    role: str | None = None
    signature: str | None = None
    date: str | None = None


@dataclass(slots=True)
class ReportSignaturePage:
    """报告签署页。"""

    signers: list[ReportSigner] = field(default_factory=list)
    title: str | None = None
    layout_template: str | None = _alias_field("layoutTemplate", default=None)


@dataclass(slots=True)
class BackCoverConfig:
    """PPT/分页报告封底配置。"""

    image: str | None = None
    text: str | None = None


@dataclass(slots=True)
class ReportSlide:
    """分页/PPT 报告中的单页。"""

    id: str
    layout: ReportLayout
    components: list[ReportComponent] = field(default_factory=list)
    title: str | None = None
    description: str | None = None


@dataclass(slots=True)
class ReportSlideSection:
    """分页/PPT 报告中的页面分组。"""

    id: str
    type: str = "section"
    slides: list[ReportSlide] = field(default_factory=list)
    title: str | None = None
    description: str | None = None


ReportPagedContentItem = ReportSlide | ReportSlideSection


@dataclass(slots=True)
class ReportDsl:
    """正式报告 DSL 聚合。"""

    basic_info: ReportBasicInfo = _alias_field("basicInfo")
    structure_type: str = _alias_field("structureType", default="flow")
    cover: ReportCover | None = None
    back_cover: BackCoverConfig | None = _alias_field("backCover", default=None)
    signature_page: ReportSignaturePage | None = _alias_field("signaturePage", default=None)
    catalogs: list[ReportCatalog] = field(default_factory=list)
    layout: ReportLayout | None = None
    content: list[ReportPagedContentItem] = field(default_factory=list)
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
    user_id: str = _alias_field("userId")
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
    set_value(payload, TemplateInstance, "structure_type", instance.structure_type or "flow")
    set_value(payload, TemplateInstance, "parameters", [parameter_to_dict(item) for item in instance.parameters])
    set_value(payload, TemplateInstance, "parameter_confirmation", parameter_confirmation_to_dict(instance.parameter_confirmation))
    if (instance.structure_type or "flow") == "paged":
        set_value(payload, TemplateInstance, "chapters", [template_instance_chapter_to_dict(item) for item in instance.chapters])
    else:
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
        structure_type=str(get_value(payload, TemplateInstance, "structure_type") or "flow"),
        parameters=[parameter_from_dict(item) for item in list(get_value(payload, TemplateInstance, "parameters") or [])],
        parameter_confirmation=parameter_confirmation_from_dict(get_value(payload, TemplateInstance, "parameter_confirmation")),
        catalogs=[template_instance_catalog_from_dict(item) for item in list(get_value(payload, TemplateInstance, "catalogs") or [])],
        chapters=[template_instance_chapter_from_dict(item) for item in list(get_value(payload, TemplateInstance, "chapters") or [])],
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


def dynamic_context_to_dict(item: DynamicContext) -> dict[str, Any]:
    payload: dict[str, Any] = {"type": item.type}
    if item.parameter_id is not None:
        set_value(payload, DynamicContext, "parameter_id", item.parameter_id)
    if item.item_value is not None:
        set_value(payload, DynamicContext, "item_value", parameter_value_to_dict(item.item_value))
    if item.case_id is not None:
        set_value(payload, DynamicContext, "case_id", item.case_id)
    if item.url is not None:
        payload["url"] = item.url
    if item.node_type is not None:
        set_value(payload, DynamicContext, "node_type", item.node_type)
    return payload


def dynamic_context_from_dict(payload: Any) -> DynamicContext | None:
    if not isinstance(payload, dict):
        foreach_context = foreach_context_from_dict(payload)
        return dynamic_context_from_foreach(foreach_context)
    return DynamicContext(
        type=str(payload.get("type") or ""),
        parameter_id=_as_optional_str(get_value(payload, DynamicContext, "parameter_id")),
        item_value=parameter_value_from_dict(get_value(payload, DynamicContext, "item_value")) if isinstance(get_value(payload, DynamicContext, "item_value"), dict) else None,
        case_id=_as_optional_str(get_value(payload, DynamicContext, "case_id")),
        url=_as_optional_str(payload.get("url")),
        node_type=_as_optional_str(get_value(payload, DynamicContext, "node_type")),
    )


def dynamic_context_from_foreach(context: ForeachContext | None) -> DynamicContext | None:
    if context is None:
        return None
    item_value = context.item_values[0] if context.item_values else None
    return DynamicContext(type="foreach", parameter_id=context.parameter_id, item_value=item_value)


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
    if block.properties is not None:
        from ...template_catalog.domain.models import presentation_property_to_dict

        payload["properties"] = presentation_property_to_dict(block.properties)
    if block.description is not None:
        set_value(payload, TemplateInstancePresentationBlock, "description", block.description)
    if block.parts:
        set_value(payload, TemplateInstancePresentationBlock, "parts", [template_instance_composite_table_part_to_dict(item) for item in block.parts])
    return payload


def template_instance_presentation_block_from_dict(payload: dict[str, Any]) -> TemplateInstancePresentationBlock:
    properties = _presentation_property_from_any(payload.get("properties"))
    properties = presentation_property_with_text(
        properties,
        template=_as_optional_str(payload.get("template")),
        content=_as_optional_str(payload.get("content")),
    )
    return TemplateInstancePresentationBlock(
        id=str(get_value(payload, TemplateInstancePresentationBlock, "id") or ""),
        type=str(get_value(payload, TemplateInstancePresentationBlock, "type") or ""),
        title=_as_optional_str(get_value(payload, TemplateInstancePresentationBlock, "title")),
        dataset_id=_as_optional_str(get_value(payload, TemplateInstancePresentationBlock, "dataset_id")),
        properties=properties,
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
    dynamic_context = section.dynamic_context or dynamic_context_from_foreach(section.foreach_context)
    if dynamic_context is not None:
        set_value(payload, TemplateInstanceSection, "dynamic_context", dynamic_context_to_dict(dynamic_context))
    return payload


def template_instance_section_from_dict(payload: dict[str, Any]) -> TemplateInstanceSection:
    legacy_foreach_context = foreach_context_from_dict(get_value(payload, TemplateInstanceSection, "foreach_context"))
    dynamic_context = dynamic_context_from_dict(get_value(payload, TemplateInstanceSection, "dynamic_context")) or dynamic_context_from_foreach(legacy_foreach_context)
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
        dynamic_context=dynamic_context,
        foreach_context=legacy_foreach_context,
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
    dynamic_context = catalog.dynamic_context or dynamic_context_from_foreach(catalog.foreach_context)
    if dynamic_context is not None:
        set_value(payload, TemplateInstanceCatalog, "dynamic_context", dynamic_context_to_dict(dynamic_context))
    if catalog.sub_catalogs:
        set_value(payload, TemplateInstanceCatalog, "sub_catalogs", [template_instance_catalog_to_dict(item) for item in catalog.sub_catalogs])
    if catalog.sections:
        set_value(payload, TemplateInstanceCatalog, "sections", [template_instance_section_to_dict(item) for item in catalog.sections])
    return payload


def template_instance_catalog_from_dict(payload: dict[str, Any]) -> TemplateInstanceCatalog:
    legacy_foreach_context = foreach_context_from_dict(get_value(payload, TemplateInstanceCatalog, "foreach_context"))
    dynamic_context = dynamic_context_from_dict(get_value(payload, TemplateInstanceCatalog, "dynamic_context")) or dynamic_context_from_foreach(legacy_foreach_context)
    return TemplateInstanceCatalog(
        id=str(get_value(payload, TemplateInstanceCatalog, "id") or ""),
        title=str(get_value(payload, TemplateInstanceCatalog, "title") or ""),
        rendered_title=str(get_value(payload, TemplateInstanceCatalog, "rendered_title") or ""),
        description=_as_optional_str(get_value(payload, TemplateInstanceCatalog, "description")),
        order=_as_optional_int(get_value(payload, TemplateInstanceCatalog, "order")),
        parameters=[parameter_from_dict(item) for item in list(get_value(payload, TemplateInstanceCatalog, "parameters") or [])],
        dynamic_context=dynamic_context,
        foreach_context=legacy_foreach_context,
        sub_catalogs=[template_instance_catalog_from_dict(item) for item in list(get_value(payload, TemplateInstanceCatalog, "sub_catalogs") or [])],
        sections=[template_instance_section_from_dict(item) for item in list(get_value(payload, TemplateInstanceCatalog, "sections") or [])],
    )


def template_instance_slide_to_dict(slide: TemplateInstanceSlide) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, TemplateInstanceSlide, "id", slide.id)
    if slide.title is not None:
        set_value(payload, TemplateInstanceSlide, "title", slide.title)
    if slide.subtitle is not None:
        set_value(payload, TemplateInstanceSlide, "subtitle", slide.subtitle)
    if slide.description is not None:
        set_value(payload, TemplateInstanceSlide, "description", slide.description)
    if slide.order is not None:
        set_value(payload, TemplateInstanceSlide, "order", slide.order)
    if slide.parameters:
        set_value(payload, TemplateInstanceSlide, "parameters", [parameter_to_dict(item) for item in slide.parameters])
    if slide.dynamic_context is not None:
        set_value(payload, TemplateInstanceSlide, "dynamic_context", dynamic_context_to_dict(slide.dynamic_context))
    if slide.layout is not None:
        set_value(payload, TemplateInstanceSlide, "layout", slide_layout_to_dict(slide.layout))
    set_value(payload, TemplateInstanceSlide, "sections", [template_instance_section_to_dict(item) for item in slide.sections])
    return payload


def template_instance_slide_from_dict(payload: dict[str, Any]) -> TemplateInstanceSlide:
    return TemplateInstanceSlide(
        id=str(get_value(payload, TemplateInstanceSlide, "id") or ""),
        title=_as_optional_str(get_value(payload, TemplateInstanceSlide, "title")),
        subtitle=_as_optional_str(get_value(payload, TemplateInstanceSlide, "subtitle")),
        description=_as_optional_str(get_value(payload, TemplateInstanceSlide, "description")),
        order=_as_optional_int(get_value(payload, TemplateInstanceSlide, "order")),
        parameters=[parameter_from_dict(item) for item in list(get_value(payload, TemplateInstanceSlide, "parameters") or [])],
        dynamic_context=dynamic_context_from_dict(get_value(payload, TemplateInstanceSlide, "dynamic_context")),
        layout=slide_layout_from_dict(get_value(payload, TemplateInstanceSlide, "layout")),
        sections=[template_instance_section_from_dict(item) for item in list(get_value(payload, TemplateInstanceSlide, "sections") or [])],
    )


def template_instance_chapter_to_dict(chapter: TemplateInstanceChapter) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, TemplateInstanceChapter, "id", chapter.id)
    if chapter.title is not None:
        set_value(payload, TemplateInstanceChapter, "title", chapter.title)
    if chapter.description is not None:
        set_value(payload, TemplateInstanceChapter, "description", chapter.description)
    if chapter.implicit is not None:
        set_value(payload, TemplateInstanceChapter, "implicit", chapter.implicit)
    if chapter.order is not None:
        set_value(payload, TemplateInstanceChapter, "order", chapter.order)
    if chapter.parameters:
        set_value(payload, TemplateInstanceChapter, "parameters", [parameter_to_dict(item) for item in chapter.parameters])
    if chapter.dynamic_context is not None:
        set_value(payload, TemplateInstanceChapter, "dynamic_context", dynamic_context_to_dict(chapter.dynamic_context))
    set_value(payload, TemplateInstanceChapter, "slides", [template_instance_slide_to_dict(item) for item in chapter.slides])
    return payload


def template_instance_chapter_from_dict(payload: dict[str, Any]) -> TemplateInstanceChapter:
    return TemplateInstanceChapter(
        id=str(get_value(payload, TemplateInstanceChapter, "id") or ""),
        title=_as_optional_str(get_value(payload, TemplateInstanceChapter, "title")),
        description=_as_optional_str(get_value(payload, TemplateInstanceChapter, "description")),
        implicit=_as_optional_bool(get_value(payload, TemplateInstanceChapter, "implicit")),
        order=_as_optional_int(get_value(payload, TemplateInstanceChapter, "order")),
        parameters=[parameter_from_dict(item) for item in list(get_value(payload, TemplateInstanceChapter, "parameters") or [])],
        dynamic_context=dynamic_context_from_dict(get_value(payload, TemplateInstanceChapter, "dynamic_context")),
        slides=[template_instance_slide_from_dict(item) for item in list(get_value(payload, TemplateInstanceChapter, "slides") or [])],
    )


def report_dsl_to_dict(report: ReportDsl) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    structure_type = str(report.structure_type or "flow")
    set_value(payload, ReportDsl, "structure_type", structure_type)
    set_value(payload, ReportDsl, "basic_info", report_basic_info_to_dict(report.basic_info))
    if report.cover is not None:
        set_value(payload, ReportDsl, "cover", report_cover_to_dict(report.cover))
    if report.back_cover is not None:
        set_value(payload, ReportDsl, "back_cover", back_cover_config_to_dict(report.back_cover))
    if report.signature_page is not None:
        set_value(payload, ReportDsl, "signature_page", report_signature_page_to_dict(report.signature_page))
    if structure_type == "paged":
        set_value(payload, ReportDsl, "content", [report_paged_content_item_to_dict(item) for item in report.content])
    else:
        set_value(payload, ReportDsl, "catalogs", [report_catalog_to_dict(item) for item in report.catalogs])
        set_value(payload, ReportDsl, "layout", report_layout_to_dict(report.layout or ReportLayout(type="grid")))
    if report.summary is not None:
        set_value(payload, ReportDsl, "summary", report_summary_to_dict(report.summary))
    if report.report_meta:
        set_value(payload, ReportDsl, "report_meta", {key: report_generate_meta_to_dict(value) for key, value in report.report_meta.items()})
    return payload


def report_dsl_from_dict(payload: dict[str, Any]) -> ReportDsl:
    structure_type = str(get_value(payload, ReportDsl, "structure_type") or "flow")
    return ReportDsl(
        structure_type=structure_type,
        basic_info=report_basic_info_from_dict(get_value(payload, ReportDsl, "basic_info") or {}),
        cover=report_cover_from_dict(get_value(payload, ReportDsl, "cover")) if isinstance(get_value(payload, ReportDsl, "cover"), dict) else None,
        back_cover=back_cover_config_from_dict(get_value(payload, ReportDsl, "back_cover")) if isinstance(get_value(payload, ReportDsl, "back_cover"), dict) else None,
        signature_page=report_signature_page_from_dict(get_value(payload, ReportDsl, "signature_page")) if isinstance(get_value(payload, ReportDsl, "signature_page"), dict) else None,
        catalogs=[report_catalog_from_dict(item) for item in list(get_value(payload, ReportDsl, "catalogs") or [])],
        layout=report_layout_from_dict(get_value(payload, ReportDsl, "layout") or {}) if isinstance(get_value(payload, ReportDsl, "layout"), dict) else None,
        content=[report_paged_content_item_from_dict(item) for item in list(get_value(payload, ReportDsl, "content") or [])],
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
    _set_if(payload, ReportBasicInfo, "asset_schema_version", info.asset_schema_version)
    _set_if(payload, ReportBasicInfo, "mode", info.mode)
    _set_if(payload, ReportBasicInfo, "status", info.status)
    _set_if(payload, ReportBasicInfo, "name", info.name)
    _set_if(payload, ReportBasicInfo, "report_type", info.report_type)
    _set_if(payload, ReportBasicInfo, "description", info.description)
    _set_if(payload, ReportBasicInfo, "template_id", info.template_id)
    _set_if(payload, ReportBasicInfo, "template_name", info.template_name)
    _set_if(payload, ReportBasicInfo, "remark", info.remark)
    _set_if(payload, ReportBasicInfo, "schema_version", info.schema_version)
    _set_if(payload, ReportBasicInfo, "create_date", info.create_date)
    _set_if(payload, ReportBasicInfo, "modify_date", info.modify_date)
    _set_if(payload, ReportBasicInfo, "creator", info.creator)
    _set_if(payload, ReportBasicInfo, "modifier", info.modifier)
    _set_if(payload, ReportBasicInfo, "header", info.header)
    _set_if(payload, ReportBasicInfo, "footer", info.footer)
    _set_if(payload, ReportBasicInfo, "category", info.category)
    return payload


def report_basic_info_from_dict(payload: dict[str, Any]) -> ReportBasicInfo:
    return ReportBasicInfo(
        id=str(get_value(payload, ReportBasicInfo, "id") or ""),
        asset_schema_version=_as_optional_str(get_value(payload, ReportBasicInfo, "asset_schema_version")),
        name=_as_optional_str(get_value(payload, ReportBasicInfo, "name")),
        report_type=_as_optional_str(get_value(payload, ReportBasicInfo, "report_type")),
        description=_as_optional_str(get_value(payload, ReportBasicInfo, "description")),
        schema_version=_as_optional_str(get_value(payload, ReportBasicInfo, "schema_version")),
        status=_as_optional_str(get_value(payload, ReportBasicInfo, "status")),
        mode=_as_optional_str(get_value(payload, ReportBasicInfo, "mode")),
        template_id=_as_optional_str(get_value(payload, ReportBasicInfo, "template_id")),
        template_name=_as_optional_str(get_value(payload, ReportBasicInfo, "template_name")),
        remark=_as_optional_str(get_value(payload, ReportBasicInfo, "remark")),
        create_date=_as_optional_str(get_value(payload, ReportBasicInfo, "create_date")),
        modify_date=_as_optional_str(get_value(payload, ReportBasicInfo, "modify_date")),
        creator=_as_optional_str(get_value(payload, ReportBasicInfo, "creator")),
        modifier=_as_optional_str(get_value(payload, ReportBasicInfo, "modifier")),
        header=_as_optional_str(get_value(payload, ReportBasicInfo, "header")),
        footer=_as_optional_str(get_value(payload, ReportBasicInfo, "footer")),
        category=_as_optional_str(get_value(payload, ReportBasicInfo, "category")),
    )


def report_summary_to_dict(summary: ReportSummary) -> dict[str, Any]:
    return {"id": summary.id, "overview": summary.overview}


def report_summary_from_dict(payload: dict[str, Any]) -> ReportSummary:
    return ReportSummary(
        id=str(payload.get("id") or ""),
        overview=str(payload.get("overview") or payload.get("content") or ""),
    )


def report_additional_info_to_dict(item: ReportAdditionalInfo) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, ReportAdditionalInfo, "type", item.type)
    _set_if(payload, ReportAdditionalInfo, "name", item.name)
    set_value(payload, ReportAdditionalInfo, "value", item.value)
    _set_if(payload, ReportAdditionalInfo, "appendix", item.appendix)
    return payload


def report_additional_info_from_dict(payload: dict[str, Any]) -> ReportAdditionalInfo:
    return ReportAdditionalInfo(
        type=str(payload.get("type") or ""),
        value=str(payload.get("value") if payload.get("value") is not None else payload.get("content") or ""),
        name=_as_optional_str(payload.get("name")),
        appendix=_as_optional_str(payload.get("appendix")),
    )


def report_generate_meta_to_dict(meta: ReportGenerateMeta) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, ReportGenerateMeta, "status", meta.status)
    set_value(payload, ReportGenerateMeta, "question", meta.question)
    if meta.additional_infos:
        set_value(payload, ReportGenerateMeta, "additional_infos", [report_additional_info_to_dict(item) for item in meta.additional_infos])
    if meta.outline is not None:
        set_value(payload, ReportGenerateMeta, "outline", outline_definition_to_dict(meta.outline))
    if meta.parameters:
        set_value(payload, ReportGenerateMeta, "parameters", {key: parameter_to_dict(value) for key, value in meta.parameters.items()})
    return payload


def report_generate_meta_from_dict(payload: dict[str, Any]) -> ReportGenerateMeta:
    additional_infos = [
        report_additional_info_from_dict(item)
        for item in list(payload.get("additionalInfos") or payload.get("additionalInfo") or [])
        if isinstance(item, dict)
    ]
    legacy_meta_fields = [
        ("prompt", "Prompt"),
        ("summary", "Summary"),
        ("sql", "SQL"),
        ("api", "API"),
        ("knowledge", "Knowledge"),
    ]
    for field_name, info_type in legacy_meta_fields:
        value = payload.get(field_name)
        if value is not None:
            additional_infos.append(ReportAdditionalInfo(type=info_type, value=str(value)))
    return ReportGenerateMeta(
        status=str(get_value(payload, ReportGenerateMeta, "status") or ""),
        question=str(get_value(payload, ReportGenerateMeta, "question") or ""),
        additional_infos=additional_infos,
        outline=_outline_from_any(payload.get("outline")) if isinstance(payload.get("outline"), dict) else None,
        parameters={
            str(key): parameter_from_dict(value)
            for key, value in dict(get_value(payload, ReportGenerateMeta, "parameters") or {}).items()
            if isinstance(value, dict)
        },
    )


def report_layout_to_dict(layout: ReportLayout) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, ReportLayout, "type", layout.type)
    _set_if(payload, ReportLayout, "auto_layout", layout.auto_layout)
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
    return ReportLayout(
        type=str(get_value(payload, ReportLayout, "type") or ""),
        auto_layout=_as_optional_bool(get_value(payload, ReportLayout, "auto_layout")),
        grid=grid,
    )


def report_column_to_dict(column: ReportColumn) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, ReportColumn, "key", column.key)
    set_value(payload, ReportColumn, "title", column.title)
    _set_if(payload, ReportColumn, "type", column.type)
    _set_if(payload, ReportColumn, "width", column.width)
    _set_if(payload, ReportColumn, "sortable", column.sortable)
    _set_if(payload, ReportColumn, "filterable", column.filterable)
    if column.children:
        set_value(payload, ReportColumn, "children", [report_column_to_dict(item) for item in column.children])
    return payload


def report_column_from_dict(payload: dict[str, Any]) -> ReportColumn:
    return ReportColumn(
        key=str(payload.get("key") or ""),
        title=str(payload.get("title") or ""),
        type=_as_optional_str(payload.get("type")),
        width=payload.get("width"),
        sortable=_as_optional_bool(payload.get("sortable")),
        filterable=_as_optional_bool(payload.get("filterable")),
        align=_as_optional_str(payload.get("align")),
        children=[report_column_from_dict(item) for item in list(payload.get("children") or [])],
    )


def _set_component_common(payload: dict[str, Any], model_type: type, component: Any) -> None:
    _set_if(payload, model_type, "layout", component.layout)
    _set_if(payload, model_type, "basic_properties", component.basic_properties)
    _set_if(payload, model_type, "advance_properties", component.advance_properties)
    if component.interactions:
        set_value(payload, model_type, "interactions", component.interactions)


def _component_common_kwargs(payload: dict[str, Any], model_type: type) -> dict[str, Any]:
    return {
        "layout": get_value(payload, model_type, "layout") if isinstance(get_value(payload, model_type, "layout"), dict) else None,
        "basic_properties": get_value(payload, model_type, "basic_properties") if isinstance(get_value(payload, model_type, "basic_properties"), dict) else None,
        "advance_properties": get_value(payload, model_type, "advance_properties") if isinstance(get_value(payload, model_type, "advance_properties"), dict) else None,
        "interactions": list(get_value(payload, model_type, "interactions") or []),
    }


def markdown_component_to_dict(component: MarkdownComponent) -> dict[str, Any]:
    payload = {
        get_alias(MarkdownComponent, "id"): component.id,
        get_alias(MarkdownComponent, "type"): component.type,
        get_alias(MarkdownComponent, "data_properties"): {
            get_alias(MarkdownDataProperties, "data_type"): component.data_properties.data_type,
            "content": component.data_properties.content,
        },
    }
    data_properties = payload[get_alias(MarkdownComponent, "data_properties")]
    _set_if(data_properties, MarkdownDataProperties, "source_id", component.data_properties.source_id)
    _set_if(data_properties, MarkdownDataProperties, "url", component.data_properties.url)
    _set_if(data_properties, MarkdownDataProperties, "method", component.data_properties.method)
    _set_if(data_properties, MarkdownDataProperties, "auto_refresh", component.data_properties.auto_refresh)
    _set_if(data_properties, MarkdownDataProperties, "refresh_interval", component.data_properties.refresh_interval)
    _set_component_common(payload, MarkdownComponent, component)
    return payload


def markdown_component_from_dict(payload: dict[str, Any]) -> MarkdownComponent:
    data = get_value(payload, MarkdownComponent, "data_properties") if isinstance(get_value(payload, MarkdownComponent, "data_properties"), dict) else {}
    return MarkdownComponent(
        id=str(get_value(payload, MarkdownComponent, "id") or ""),
        type=str(get_value(payload, MarkdownComponent, "type") or ""),
        data_properties=MarkdownDataProperties(
            data_type=str(data.get(get_alias(MarkdownDataProperties, "data_type")) or ""),
            content=str(data.get("content") or ""),
            source_id=_as_optional_str(data.get(get_alias(MarkdownDataProperties, "source_id"))),
            url=_as_optional_str(data.get(get_alias(MarkdownDataProperties, "url"))),
            method=_as_optional_str(data.get(get_alias(MarkdownDataProperties, "method"))),
            auto_refresh=_as_optional_bool(data.get(get_alias(MarkdownDataProperties, "auto_refresh"))),
            refresh_interval=_as_optional_float(data.get(get_alias(MarkdownDataProperties, "refresh_interval"))),
        ),
        **_component_common_kwargs(payload, MarkdownComponent),
    )


def text_component_to_dict(component: TextComponent) -> dict[str, Any]:
    payload = {
        get_alias(TextComponent, "id"): component.id,
        get_alias(TextComponent, "type"): component.type,
        get_alias(TextComponent, "data_properties"): {
            get_alias(TextDataProperties, "data_type"): component.data_properties.data_type,
            "content": component.data_properties.content,
        },
    }
    data_properties = payload[get_alias(TextComponent, "data_properties")]
    _set_if(data_properties, TextDataProperties, "source_id", component.data_properties.source_id)
    _set_if(data_properties, TextDataProperties, "url", component.data_properties.url)
    _set_if(data_properties, TextDataProperties, "method", component.data_properties.method)
    _set_if(data_properties, TextDataProperties, "auto_refresh", component.data_properties.auto_refresh)
    _set_if(data_properties, TextDataProperties, "refresh_interval", component.data_properties.refresh_interval)
    _set_if(data_properties, TextDataProperties, "title", component.data_properties.title)
    _set_component_common(payload, TextComponent, component)
    return payload


def text_component_from_dict(payload: dict[str, Any]) -> TextComponent:
    data = get_value(payload, TextComponent, "data_properties") if isinstance(get_value(payload, TextComponent, "data_properties"), dict) else {}
    return TextComponent(
        id=str(get_value(payload, TextComponent, "id") or ""),
        type=str(get_value(payload, TextComponent, "type") or ""),
        data_properties=TextDataProperties(
            data_type=str(data.get(get_alias(TextDataProperties, "data_type")) or ""),
            content=str(data.get("content") or ""),
            source_id=_as_optional_str(data.get(get_alias(TextDataProperties, "source_id"))),
            url=_as_optional_str(data.get(get_alias(TextDataProperties, "url"))),
            method=_as_optional_str(data.get(get_alias(TextDataProperties, "method"))),
            auto_refresh=_as_optional_bool(data.get(get_alias(TextDataProperties, "auto_refresh"))),
            refresh_interval=_as_optional_float(data.get(get_alias(TextDataProperties, "refresh_interval"))),
            title=_as_optional_str(data.get(get_alias(TextDataProperties, "title"))),
        ),
        **_component_common_kwargs(payload, TextComponent),
    )


def merge_row_info_to_dict(config: MergeRowInfo) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, MergeRowInfo, "start_row_index", config.start_row_index)
    set_value(payload, MergeRowInfo, "row_span", config.row_span)
    payload["column"] = config.column
    if config.merged_text is not None:
        set_value(payload, MergeRowInfo, "merged_text", config.merged_text)
    return payload


def merge_row_info_from_dict(payload: dict[str, Any]) -> MergeRowInfo:
    return MergeRowInfo(
        start_row_index=int(get_value(payload, MergeRowInfo, "start_row_index") or 0),
        row_span=int(get_value(payload, MergeRowInfo, "row_span") or 0),
        column=str(payload.get("column") or ""),
        merged_text=_as_optional_str(get_value(payload, MergeRowInfo, "merged_text")),
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
    _set_if(data_properties, TableDataProperties, "url", component.data_properties.url)
    _set_if(data_properties, TableDataProperties, "method", component.data_properties.method)
    _set_if(data_properties, TableDataProperties, "auto_refresh", component.data_properties.auto_refresh)
    _set_if(data_properties, TableDataProperties, "refresh_interval", component.data_properties.refresh_interval)
    _set_if(data_properties, TableDataProperties, "title", component.data_properties.title)
    if component.data_properties.columns:
        data_properties["columns"] = [report_column_to_dict(item) for item in component.data_properties.columns]
    if component.data_properties.merge_columns:
        from ...template_catalog.domain.models import merge_column_info_to_dict

        set_value(data_properties, TableDataProperties, "merge_columns", [merge_column_info_to_dict(item) for item in component.data_properties.merge_columns])
    if component.data_properties.merge_rows:
        set_value(data_properties, TableDataProperties, "merge_rows", [merge_row_info_to_dict(item) for item in component.data_properties.merge_rows])
    if component.data_properties.data:
        data_properties["data"] = list(component.data_properties.data)
    _set_if(data_properties, TableDataProperties, "has_merge", component.data_properties.has_merge)
    _set_component_common(payload, TableComponent, component)
    return payload


def table_component_from_dict(payload: dict[str, Any]) -> TableComponent:
    data = get_value(payload, TableComponent, "data_properties") if isinstance(get_value(payload, TableComponent, "data_properties"), dict) else {}
    return TableComponent(
        id=str(get_value(payload, TableComponent, "id") or ""),
        type=str(get_value(payload, TableComponent, "type") or ""),
        data_properties=TableDataProperties(
            data_type=str(data.get(get_alias(TableDataProperties, "data_type")) or ""),
            source_id=_as_optional_str(data.get(get_alias(TableDataProperties, "source_id"))),
            url=_as_optional_str(data.get(get_alias(TableDataProperties, "url"))),
            method=_as_optional_str(data.get(get_alias(TableDataProperties, "method"))),
            auto_refresh=_as_optional_bool(data.get(get_alias(TableDataProperties, "auto_refresh"))),
            refresh_interval=_as_optional_float(data.get(get_alias(TableDataProperties, "refresh_interval"))),
            title=_as_optional_str(data.get(get_alias(TableDataProperties, "title"))),
            columns=[report_column_from_dict(item) for item in list(data.get("columns") or [])],
            merge_columns=[
                _merge_column_info_from_any(item)
                for item in list(get_value(data, TableDataProperties, "merge_columns") or [])
            ],
            merge_rows=[merge_row_info_from_dict(item) for item in list(get_value(data, TableDataProperties, "merge_rows") or [])],
            data=list(data.get("data") or []),
            has_merge=_as_optional_bool(get_value(data, TableDataProperties, "has_merge")),
        ),
        **_component_common_kwargs(payload, TableComponent),
    )


def chart_component_to_dict(component: ChartComponent) -> dict[str, Any]:
    payload = {
        get_alias(ChartComponent, "id"): component.id,
        get_alias(ChartComponent, "type"): component.type,
        get_alias(ChartComponent, "data_properties"): {
            get_alias(ChartDataProperties, "data_type"): component.data_properties.data_type,
        },
    }
    data_properties = payload[get_alias(ChartComponent, "data_properties")]
    _set_if(data_properties, ChartDataProperties, "source_id", component.data_properties.source_id)
    _set_if(data_properties, ChartDataProperties, "url", component.data_properties.url)
    _set_if(data_properties, ChartDataProperties, "method", component.data_properties.method)
    _set_if(data_properties, ChartDataProperties, "auto_refresh", component.data_properties.auto_refresh)
    _set_if(data_properties, ChartDataProperties, "refresh_interval", component.data_properties.refresh_interval)
    _set_if(data_properties, ChartDataProperties, "title", component.data_properties.title)
    if component.data_properties.columns:
        data_properties["columns"] = [report_column_to_dict(item) for item in component.data_properties.columns]
    if component.data_properties.data:
        data_properties["data"] = list(component.data_properties.data)
    if component.data_properties.series:
        data_properties["series"] = list(component.data_properties.series)
    if component.data_properties.axis_group:
        set_value(data_properties, ChartDataProperties, "axis_group", list(component.data_properties.axis_group))
    _set_if(data_properties, ChartDataProperties, "x_axis", component.data_properties.x_axis)
    _set_if(data_properties, ChartDataProperties, "y_axis", component.data_properties.y_axis)
    _set_component_common(payload, ChartComponent, component)
    return payload


def chart_component_from_dict(payload: dict[str, Any]) -> ChartComponent:
    data = get_value(payload, ChartComponent, "data_properties") if isinstance(get_value(payload, ChartComponent, "data_properties"), dict) else {}
    return ChartComponent(
        id=str(get_value(payload, ChartComponent, "id") or ""),
        type=str(get_value(payload, ChartComponent, "type") or ""),
        data_properties=ChartDataProperties(
            data_type=str(data.get(get_alias(ChartDataProperties, "data_type")) or ""),
            source_id=_as_optional_str(data.get(get_alias(ChartDataProperties, "source_id"))),
            url=_as_optional_str(data.get(get_alias(ChartDataProperties, "url"))),
            method=_as_optional_str(data.get(get_alias(ChartDataProperties, "method"))),
            auto_refresh=_as_optional_bool(data.get(get_alias(ChartDataProperties, "auto_refresh"))),
            refresh_interval=_as_optional_float(data.get(get_alias(ChartDataProperties, "refresh_interval"))),
            title=_as_optional_str(data.get(get_alias(ChartDataProperties, "title"))),
            columns=[report_column_from_dict(item) for item in list(data.get("columns") or [])],
            data=list(data.get("data") or []),
            series=list(data.get("series") or []),
            axis_group=[str(item) for item in list(get_value(data, ChartDataProperties, "axis_group") or [])],
            x_axis=get_value(data, ChartDataProperties, "x_axis") or payload.get("xAxis"),
            y_axis=get_value(data, ChartDataProperties, "y_axis") or payload.get("yAxis"),
        ),
        **_component_common_kwargs(payload, ChartComponent),
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
    data_properties = payload[get_alias(CompositeTableComponent, "data_properties")]
    _set_if(data_properties, CompositeTableDataProperties, "source_id", component.data_properties.source_id)
    _set_if(data_properties, CompositeTableDataProperties, "url", component.data_properties.url)
    _set_if(data_properties, CompositeTableDataProperties, "method", component.data_properties.method)
    _set_if(data_properties, CompositeTableDataProperties, "auto_refresh", component.data_properties.auto_refresh)
    _set_if(data_properties, CompositeTableDataProperties, "refresh_interval", component.data_properties.refresh_interval)
    _set_if(data_properties, CompositeTableDataProperties, "title", component.data_properties.title)
    _set_component_common(payload, CompositeTableComponent, component)
    return payload


def composite_table_component_from_dict(payload: dict[str, Any]) -> CompositeTableComponent:
    data = get_value(payload, CompositeTableComponent, "data_properties") if isinstance(get_value(payload, CompositeTableComponent, "data_properties"), dict) else {}
    return CompositeTableComponent(
        id=str(get_value(payload, CompositeTableComponent, "id") or ""),
        type=str(get_value(payload, CompositeTableComponent, "type") or ""),
        tables=[table_component_from_dict(item) for item in list(payload.get("tables") or [])],
        data_properties=CompositeTableDataProperties(
            data_type=str(data.get(get_alias(CompositeTableDataProperties, "data_type")) or ""),
            source_id=_as_optional_str(data.get(get_alias(CompositeTableDataProperties, "source_id"))),
            url=_as_optional_str(data.get(get_alias(CompositeTableDataProperties, "url"))),
            method=_as_optional_str(data.get(get_alias(CompositeTableDataProperties, "method"))),
            auto_refresh=_as_optional_bool(data.get(get_alias(CompositeTableDataProperties, "auto_refresh"))),
            refresh_interval=_as_optional_float(data.get(get_alias(CompositeTableDataProperties, "refresh_interval"))),
            title=_as_optional_str(data.get(get_alias(CompositeTableDataProperties, "title"))),
        ),
        **_component_common_kwargs(payload, CompositeTableComponent),
    )


def report_component_to_dict(component: ReportComponent) -> dict[str, Any]:
    if isinstance(component, MarkdownComponent):
        return markdown_component_to_dict(component)
    if isinstance(component, TextComponent):
        return text_component_to_dict(component)
    if isinstance(component, TableComponent):
        return table_component_to_dict(component)
    if isinstance(component, ChartComponent):
        return chart_component_to_dict(component)
    return composite_table_component_to_dict(component)


def report_component_from_dict(payload: dict[str, Any]) -> ReportComponent:
    component_type = str(payload.get("type") or "")
    if component_type == "markdown":
        return markdown_component_from_dict(payload)
    if component_type == "text":
        return text_component_from_dict(payload)
    if component_type == "table":
        return table_component_from_dict(payload)
    if component_type == "chart":
        return chart_component_from_dict(payload)
    return composite_table_component_from_dict(payload)


def report_cover_content_to_dict(item: ReportCoverContent) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, ReportCoverContent, "type", item.type)
    set_value(payload, ReportCoverContent, "content", item.content)
    set_value(payload, ReportCoverContent, "element_id", item.element_id)
    return payload


def report_cover_content_from_dict(payload: dict[str, Any]) -> ReportCoverContent:
    return ReportCoverContent(
        type=str(payload.get("type") or ""),
        content=str(payload.get("content") or ""),
        element_id=str(get_value(payload, ReportCoverContent, "element_id") or ""),
    )


def report_cover_to_dict(cover: ReportCover) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, ReportCover, "title", cover.title)
    _set_if(payload, ReportCover, "author", cover.author)
    _set_if(payload, ReportCover, "date", cover.date)
    _set_if(payload, ReportCover, "layout_template", cover.layout_template)
    _set_if(payload, ReportCover, "image", cover.image)
    if cover.contents:
        set_value(payload, ReportCover, "contents", [report_cover_content_to_dict(item) for item in cover.contents])
    return payload


def report_cover_from_dict(payload: dict[str, Any]) -> ReportCover:
    return ReportCover(
        title=str(payload.get("title") or ""),
        author=_as_optional_str(payload.get("author")),
        date=_as_optional_str(payload.get("date")),
        layout_template=_as_optional_str(get_value(payload, ReportCover, "layout_template")),
        image=_as_optional_str(payload.get("image")),
        contents=[report_cover_content_from_dict(item) for item in list(payload.get("contents") or [])],
    )


def report_signer_to_dict(signer: ReportSigner) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, ReportSigner, "name", signer.name)
    _set_if(payload, ReportSigner, "role", signer.role)
    _set_if(payload, ReportSigner, "signature", signer.signature)
    _set_if(payload, ReportSigner, "date", signer.date)
    return payload


def report_signer_from_dict(payload: dict[str, Any]) -> ReportSigner:
    return ReportSigner(
        name=str(payload.get("name") or ""),
        role=_as_optional_str(payload.get("role")),
        signature=_as_optional_str(payload.get("signature")),
        date=_as_optional_str(payload.get("date")),
    )


def report_signature_page_to_dict(page: ReportSignaturePage) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    _set_if(payload, ReportSignaturePage, "title", page.title)
    set_value(payload, ReportSignaturePage, "signers", [report_signer_to_dict(item) for item in page.signers])
    _set_if(payload, ReportSignaturePage, "layout_template", page.layout_template)
    return payload


def report_signature_page_from_dict(payload: dict[str, Any]) -> ReportSignaturePage:
    return ReportSignaturePage(
        title=_as_optional_str(payload.get("title")),
        signers=[report_signer_from_dict(item) for item in list(payload.get("signers") or [])],
        layout_template=_as_optional_str(get_value(payload, ReportSignaturePage, "layout_template")),
    )


def back_cover_config_to_dict(config: BackCoverConfig) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    _set_if(payload, BackCoverConfig, "image", config.image)
    _set_if(payload, BackCoverConfig, "text", config.text)
    return payload


def back_cover_config_from_dict(payload: dict[str, Any]) -> BackCoverConfig:
    return BackCoverConfig(
        image=_as_optional_str(get_value(payload, BackCoverConfig, "image")),
        text=_as_optional_str(get_value(payload, BackCoverConfig, "text")),
    )


def report_slide_to_dict(slide: ReportSlide) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": slide.id,
        "layout": report_layout_to_dict(slide.layout),
        "components": [report_component_to_dict(item) for item in slide.components],
    }
    _set_if(payload, ReportSlide, "title", slide.title)
    _set_if(payload, ReportSlide, "description", slide.description)
    return payload


def report_slide_from_dict(payload: dict[str, Any]) -> ReportSlide:
    return ReportSlide(
        id=str(payload.get("id") or ""),
        title=_as_optional_str(payload.get("title")),
        description=_as_optional_str(payload.get("description")),
        layout=report_layout_from_dict(payload.get("layout") or {}),
        components=[report_component_from_dict(item) for item in list(payload.get("components") or [])],
    )


def report_slide_section_to_dict(section: ReportSlideSection) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": section.id,
        "type": "section",
        "slides": [report_slide_to_dict(item) for item in section.slides],
    }
    _set_if(payload, ReportSlideSection, "title", section.title)
    _set_if(payload, ReportSlideSection, "description", section.description)
    return payload


def report_slide_section_from_dict(payload: dict[str, Any]) -> ReportSlideSection:
    return ReportSlideSection(
        id=str(payload.get("id") or ""),
        type=str(payload.get("type") or "section"),
        title=_as_optional_str(payload.get("title")),
        description=_as_optional_str(payload.get("description")),
        slides=[report_slide_from_dict(item) for item in list(payload.get("slides") or [])],
    )


def report_paged_content_item_to_dict(item: ReportPagedContentItem) -> dict[str, Any]:
    if isinstance(item, ReportSlideSection):
        return report_slide_section_to_dict(item)
    return report_slide_to_dict(item)


def report_paged_content_item_from_dict(payload: dict[str, Any]) -> ReportPagedContentItem:
    if str(payload.get("type") or "") == "section":
        return report_slide_section_from_dict(payload)
    return report_slide_from_dict(payload)


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
        description=_as_optional_str(payload.get("description")),
        layout=payload.get("layout") if isinstance(payload.get("layout"), dict) else None,
        order=_as_optional_int(payload.get("order")),
        components=[report_component_from_dict(item) for item in list(payload.get("components") or [])],
        summary=report_summary_from_dict(payload.get("summary")) if isinstance(payload.get("summary"), dict) else None,
    )


def report_catalog_to_dict(catalog: ReportCatalog) -> dict[str, Any]:
    payload: dict[str, Any] = {
        get_alias(ReportCatalog, "id"): catalog.id,
        get_alias(ReportCatalog, "name"): catalog.name or catalog.title or catalog.id,
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
        name=_as_optional_str(get_value(payload, ReportCatalog, "name") or payload.get("title")),
        title=_as_optional_str(payload.get("title")),
        description=_as_optional_str(payload.get("description")),
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


def _presentation_property_from_any(payload: Any) -> PresentationProperty | None:
    if isinstance(payload, PresentationProperty):
        return payload
    if isinstance(payload, dict):
        from ...template_catalog.domain.models import presentation_property_from_dict

        return presentation_property_from_dict(payload)
    return None


def _merge_column_info_from_any(payload: Any) -> MergeColumnInfo:
    if isinstance(payload, MergeColumnInfo):
        return payload
    if isinstance(payload, dict):
        from ...template_catalog.domain.models import merge_column_info_from_dict

        return merge_column_info_from_dict(payload)
    return MergeColumnInfo(title="", columns=[])


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


def _as_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None
