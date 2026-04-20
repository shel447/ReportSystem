"""静态报告模板目录及其递归属性的领域模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypeVar

from ....shared.kernel.dataclass_aliases import get_alias, get_value, set_value

Scalar = str | int | float | bool


def _alias_field(alias: str, **kwargs: Any):
    """为 dataclass 字段声明公开 JSON 别名。"""

    metadata = dict(kwargs.pop("metadata", {}))
    metadata["alias"] = alias
    return field(metadata=metadata, **kwargs)


@dataclass(slots=True)
class ParameterValue:
    """参数值三通道。"""

    label: Scalar
    value: Scalar
    query: Scalar


@dataclass(slots=True)
class ParameterRuntimeContext:
    """参数运行时上下文。"""

    value_source: str | None = _alias_field("valueSource", default=None)
    query_context: dict[str, Any] | None = _alias_field("queryContext", default=None)
    confirmed: bool | None = None
    confirmed_at: str | None = _alias_field("confirmedAt", default=None)
    option_source: str | None = _alias_field("optionSource", default=None)
    options_fetched_at: str | None = _alias_field("optionsFetchedAt", default=None)


@dataclass(slots=True)
class Parameter:
    """模板与模板实例共用的参数定义。"""

    id: str
    label: str
    input_type: str = _alias_field("inputType")
    required: bool
    multi: bool
    interaction_mode: str = _alias_field("interactionMode")
    description: str | None = None
    placeholder: str | None = None
    default_value: list[ParameterValue] = _alias_field("defaultValue", default_factory=list)
    options: list[ParameterValue] = field(default_factory=list)
    values: list[ParameterValue] = field(default_factory=list)
    runtime_context: ParameterRuntimeContext | None = _alias_field("runtimeContext", default=None)
    source: str | None = None


@dataclass(slots=True)
class RequirementItem:
    """诉求要素定义。"""

    id: str
    label: str
    kind: str
    required: bool
    multi: bool = False
    description: str | None = None
    source_parameter_id: str | None = _alias_field("sourceParameterId", default=None)
    widget: str | None = None
    default_value: list[ParameterValue] = _alias_field("defaultValue", default_factory=list)
    values: list[ParameterValue] = field(default_factory=list)
    value_source: str | None = _alias_field("valueSource", default=None)


@dataclass(slots=True)
class OutlineDefinition:
    """章节诉求定义。"""

    requirement: str
    items: list[RequirementItem] = field(default_factory=list)
    rendered_requirement: str | None = _alias_field("renderedRequirement", default=None)


@dataclass(slots=True)
class ForeachDefinition:
    """模板级 foreach 定义。"""

    parameter_id: str = _alias_field("parameterId")
    alias: str = _alias_field("as")


@dataclass(slots=True)
class DatasetDefinition:
    """章节数据集定义。"""

    id: str
    source_type: str = _alias_field("sourceType")
    source_ref: str = _alias_field("sourceRef")
    name: str | None = None
    depends_on: list[str] = _alias_field("dependsOn", default_factory=list)
    description: str | None = None


@dataclass(slots=True)
class CompositeTableColumn:
    """复合表列定义。"""

    key: str
    title: str
    width: str | None = None
    align: str | None = None


@dataclass(slots=True)
class CompositeTablePartLayout:
    """复合表分片布局定义。"""

    kind: str
    show_header: bool | None = _alias_field("showHeader", default=None)
    columns: list[CompositeTableColumn] = field(default_factory=list)


@dataclass(slots=True)
class SummaryRowDef:
    """摘要行定义。"""

    id: str
    title: str


@dataclass(slots=True)
class SummaryTableSpec:
    """摘要分片定义。"""

    part_ids: list[str] = _alias_field("partIds", default_factory=list)
    rows: list[SummaryRowDef] = field(default_factory=list)
    prompt: str | None = None


@dataclass(slots=True)
class CompositeTablePart:
    """复合表分片定义。"""

    id: str
    title: str
    source_type: str = _alias_field("sourceType")
    description: str | None = None
    dataset_id: str | None = _alias_field("datasetId", default=None)
    summary_spec: SummaryTableSpec | None = _alias_field("summarySpec", default=None)
    table_layout: CompositeTablePartLayout | None = _alias_field("tableLayout", default=None)


@dataclass(slots=True)
class PresentationBlock:
    """章节展示块定义。"""

    id: str
    type: str
    title: str | None = None
    dataset_id: str | None = _alias_field("datasetId", default=None)
    description: str | None = None
    parts: list[CompositeTablePart] = field(default_factory=list)


@dataclass(slots=True)
class PresentationDefinition:
    """章节展示定义。"""

    kind: str
    blocks: list[PresentationBlock] = field(default_factory=list)


@dataclass(slots=True)
class SectionContentDefinition:
    """章节内容定义。"""

    presentation: PresentationDefinition
    datasets: list[DatasetDefinition] = field(default_factory=list)


@dataclass(slots=True)
class SectionDefinition:
    """章节定义。"""

    id: str
    outline: OutlineDefinition
    content: SectionContentDefinition
    description: str | None = None
    parameters: list[Parameter] = field(default_factory=list)
    foreach: ForeachDefinition | None = None


@dataclass(slots=True)
class CatalogDefinition:
    """目录定义。"""

    id: str
    title: str
    description: str | None = None
    parameters: list[Parameter] = field(default_factory=list)
    foreach: ForeachDefinition | None = None
    sub_catalogs: list["CatalogDefinition"] = _alias_field("subCatalogs", default_factory=list)
    sections: list[SectionDefinition] = field(default_factory=list)


@dataclass(slots=True)
class ReportTemplate:
    """模板目录与运行时共用的正式静态模板聚合。"""

    id: str
    category: str
    name: str
    description: str
    schema_version: str = _alias_field("schemaVersion")
    parameters: list[Parameter] = field(default_factory=list)
    catalogs: list[CatalogDefinition] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: datetime | None = _alias_field("createdAt", default=None)
    updated_at: datetime | None = _alias_field("updatedAt", default=None)


@dataclass(slots=True)
class TemplateSummary:
    """用于列表页和轻量选择器的紧凑投影。"""

    id: str
    category: str
    name: str
    description: str
    schema_version: str = _alias_field("schemaVersion")
    updated_at: datetime | None = _alias_field("updatedAt", default=None)


@dataclass(slots=True)
class TemplateMatchCandidate:
    """当模板排序外置时使用的语义匹配候选投影。"""

    template_id: str = _alias_field("templateId")
    template_name: str = _alias_field("templateName")
    category: str
    description: str
    score: float
    reasons: list[str] = field(default_factory=list)


T = TypeVar("T")


def report_template_from_dict(payload: dict[str, Any]) -> ReportTemplate:
    """把模板 JSON 契约转换为领域 dataclass。"""
    return ReportTemplate(
        id=str(get_value(payload, ReportTemplate, "id") or ""),
        category=str(get_value(payload, ReportTemplate, "category") or ""),
        name=str(get_value(payload, ReportTemplate, "name") or ""),
        description=str(get_value(payload, ReportTemplate, "description") or ""),
        schema_version=str(get_value(payload, ReportTemplate, "schema_version") or ""),
        parameters=[parameter_from_dict(item) for item in list(get_value(payload, ReportTemplate, "parameters") or [])],
        catalogs=[catalog_definition_from_dict(item) for item in list(get_value(payload, ReportTemplate, "catalogs") or [])],
        tags=[str(item) for item in list(get_value(payload, ReportTemplate, "tags") or [])],
        created_at=_as_datetime(get_value(payload, ReportTemplate, "created_at")),
        updated_at=_as_datetime(get_value(payload, ReportTemplate, "updated_at")),
    )


def report_template_to_dict(template: ReportTemplate) -> dict[str, Any]:
    """把模板领域对象投影为公开 JSON 契约。"""
    payload: dict[str, Any] = {}
    set_value(payload, ReportTemplate, "id", template.id)
    set_value(payload, ReportTemplate, "category", template.category)
    set_value(payload, ReportTemplate, "name", template.name)
    set_value(payload, ReportTemplate, "description", template.description)
    set_value(payload, ReportTemplate, "schema_version", template.schema_version)
    set_value(payload, ReportTemplate, "tags", list(template.tags))
    set_value(payload, ReportTemplate, "parameters", [parameter_to_dict(item) for item in template.parameters])
    set_value(payload, ReportTemplate, "catalogs", [catalog_definition_to_dict(item) for item in template.catalogs])
    set_value(payload, ReportTemplate, "created_at", _isoformat(template.created_at))
    set_value(payload, ReportTemplate, "updated_at", _isoformat(template.updated_at))
    return payload


def parameter_from_dict(payload: dict[str, Any]) -> Parameter:
    return Parameter(
        id=str(get_value(payload, Parameter, "id") or ""),
        label=str(get_value(payload, Parameter, "label") or ""),
        input_type=str(get_value(payload, Parameter, "input_type") or ""),
        required=bool(get_value(payload, Parameter, "required")),
        multi=bool(get_value(payload, Parameter, "multi")),
        interaction_mode=str(get_value(payload, Parameter, "interaction_mode") or ""),
        description=_as_optional_str(get_value(payload, Parameter, "description")),
        placeholder=_as_optional_str(get_value(payload, Parameter, "placeholder")),
        default_value=[parameter_value_from_dict(item) for item in list(get_value(payload, Parameter, "default_value") or [])],
        options=[parameter_value_from_dict(item) for item in list(get_value(payload, Parameter, "options") or [])],
        values=[parameter_value_from_dict(item) for item in list(get_value(payload, Parameter, "values") or [])],
        runtime_context=parameter_runtime_context_from_dict(get_value(payload, Parameter, "runtime_context")),
        source=_as_optional_str(get_value(payload, Parameter, "source")),
    )


def parameter_to_dict(parameter: Parameter) -> dict[str, Any]:
    payload: dict[str, Any] = {
        get_alias(Parameter, "id"): parameter.id,
        get_alias(Parameter, "label"): parameter.label,
    }
    set_value(payload, Parameter, "input_type", parameter.input_type)
    set_value(payload, Parameter, "required", parameter.required)
    set_value(payload, Parameter, "multi", parameter.multi)
    set_value(payload, Parameter, "interaction_mode", parameter.interaction_mode)
    if parameter.description is not None:
        set_value(payload, Parameter, "description", parameter.description)
    if parameter.placeholder is not None:
        set_value(payload, Parameter, "placeholder", parameter.placeholder)
    if parameter.default_value:
        set_value(payload, Parameter, "default_value", [parameter_value_to_dict(item) for item in parameter.default_value])
    if parameter.options or parameter.input_type == "enum":
        set_value(payload, Parameter, "options", [parameter_value_to_dict(item) for item in parameter.options])
    if parameter.values:
        set_value(payload, Parameter, "values", [parameter_value_to_dict(item) for item in parameter.values])
    if parameter.runtime_context is not None:
        set_value(payload, Parameter, "runtime_context", parameter_runtime_context_to_dict(parameter.runtime_context))
    if parameter.source is not None:
        set_value(payload, Parameter, "source", parameter.source)
    return payload


def parameter_value_from_dict(payload: dict[str, Any]) -> ParameterValue:
    return ParameterValue(
        label=payload.get("label"),
        value=payload.get("value"),
        query=payload.get("query"),
    )


def parameter_value_to_dict(value: ParameterValue) -> dict[str, Any]:
    return {
        "label": value.label,
        "value": value.value,
        "query": value.query,
    }


def parameter_runtime_context_from_dict(payload: Any) -> ParameterRuntimeContext | None:
    if not isinstance(payload, dict):
        return None
    return ParameterRuntimeContext(
        value_source=_as_optional_str(get_value(payload, ParameterRuntimeContext, "value_source")),
        query_context=dict(get_value(payload, ParameterRuntimeContext, "query_context") or {}) or None,
        confirmed=_as_optional_bool(get_value(payload, ParameterRuntimeContext, "confirmed")),
        confirmed_at=_as_optional_str(get_value(payload, ParameterRuntimeContext, "confirmed_at")),
        option_source=_as_optional_str(get_value(payload, ParameterRuntimeContext, "option_source")),
        options_fetched_at=_as_optional_str(get_value(payload, ParameterRuntimeContext, "options_fetched_at")),
    )


def parameter_runtime_context_to_dict(context: ParameterRuntimeContext) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if context.value_source is not None:
        set_value(payload, ParameterRuntimeContext, "value_source", context.value_source)
    if context.query_context is not None:
        set_value(payload, ParameterRuntimeContext, "query_context", dict(context.query_context))
    if context.confirmed is not None:
        set_value(payload, ParameterRuntimeContext, "confirmed", context.confirmed)
    if context.confirmed_at is not None:
        set_value(payload, ParameterRuntimeContext, "confirmed_at", context.confirmed_at)
    if context.option_source is not None:
        set_value(payload, ParameterRuntimeContext, "option_source", context.option_source)
    if context.options_fetched_at is not None:
        set_value(payload, ParameterRuntimeContext, "options_fetched_at", context.options_fetched_at)
    return payload


def requirement_item_from_dict(payload: dict[str, Any]) -> RequirementItem:
    return RequirementItem(
        id=str(payload.get("id") or ""),
        label=str(payload.get("label") or ""),
        kind=str(payload.get("kind") or ""),
        required=bool(payload.get("required")),
        multi=bool(payload.get("multi")) if payload.get("multi") is not None else False,
        description=_as_optional_str(payload.get("description")),
        source_parameter_id=_as_optional_str(get_value(payload, RequirementItem, "source_parameter_id")),
        widget=_as_optional_str(payload.get("widget")),
        default_value=[parameter_value_from_dict(item) for item in list(get_value(payload, RequirementItem, "default_value") or [])],
        values=[parameter_value_from_dict(item) for item in list(payload.get("values") or [])],
        value_source=_as_optional_str(get_value(payload, RequirementItem, "value_source")),
    )


def requirement_item_to_dict(item: RequirementItem) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": item.id,
        "label": item.label,
        "kind": item.kind,
        "required": item.required,
    }
    if item.multi:
        payload["multi"] = item.multi
    if item.description is not None:
        payload["description"] = item.description
    if item.source_parameter_id is not None:
        set_value(payload, RequirementItem, "source_parameter_id", item.source_parameter_id)
    if item.widget is not None:
        payload["widget"] = item.widget
    if item.default_value:
        set_value(payload, RequirementItem, "default_value", [parameter_value_to_dict(value) for value in item.default_value])
    if item.values:
        payload["values"] = [parameter_value_to_dict(value) for value in item.values]
    if item.value_source is not None:
        set_value(payload, RequirementItem, "value_source", item.value_source)
    return payload


def outline_definition_from_dict(payload: dict[str, Any]) -> OutlineDefinition:
    return OutlineDefinition(
        requirement=str(payload.get("requirement") or ""),
        rendered_requirement=_as_optional_str(get_value(payload, OutlineDefinition, "rendered_requirement")),
        items=[requirement_item_from_dict(item) for item in list(payload.get("items") or [])],
    )


def outline_definition_to_dict(outline: OutlineDefinition) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "requirement": outline.requirement,
        "items": [requirement_item_to_dict(item) for item in outline.items],
    }
    if outline.rendered_requirement is not None:
        set_value(payload, OutlineDefinition, "rendered_requirement", outline.rendered_requirement)
    return payload


def foreach_definition_from_dict(payload: Any) -> ForeachDefinition | None:
    if not isinstance(payload, dict):
        return None
    return ForeachDefinition(
        parameter_id=str(get_value(payload, ForeachDefinition, "parameter_id") or ""),
        alias=str(get_value(payload, ForeachDefinition, "alias") or ""),
    )


def foreach_definition_to_dict(foreach: ForeachDefinition) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    set_value(payload, ForeachDefinition, "parameter_id", foreach.parameter_id)
    set_value(payload, ForeachDefinition, "alias", foreach.alias)
    return payload


def dataset_definition_from_dict(payload: dict[str, Any]) -> DatasetDefinition:
    return DatasetDefinition(
        id=str(payload.get("id") or ""),
        source_type=str(get_value(payload, DatasetDefinition, "source_type") or ""),
        source_ref=str(get_value(payload, DatasetDefinition, "source_ref") or ""),
        name=_as_optional_str(payload.get("name")),
        depends_on=[str(item) for item in list(get_value(payload, DatasetDefinition, "depends_on") or [])],
        description=_as_optional_str(payload.get("description")),
    )


def dataset_definition_to_dict(dataset: DatasetDefinition) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": dataset.id,
    }
    set_value(payload, DatasetDefinition, "source_type", dataset.source_type)
    set_value(payload, DatasetDefinition, "source_ref", dataset.source_ref)
    if dataset.name is not None:
        payload["name"] = dataset.name
    if dataset.depends_on:
        set_value(payload, DatasetDefinition, "depends_on", list(dataset.depends_on))
    if dataset.description is not None:
        payload["description"] = dataset.description
    return payload


def composite_table_column_from_dict(payload: dict[str, Any]) -> CompositeTableColumn:
    return CompositeTableColumn(
        key=str(payload.get("key") or ""),
        title=str(payload.get("title") or ""),
        width=_as_optional_str(payload.get("width")),
        align=_as_optional_str(payload.get("align")),
    )


def composite_table_column_to_dict(column: CompositeTableColumn) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "key": column.key,
        "title": column.title,
    }
    if column.width is not None:
        payload["width"] = column.width
    if column.align is not None:
        payload["align"] = column.align
    return payload


def composite_table_part_layout_from_dict(payload: Any) -> CompositeTablePartLayout | None:
    if not isinstance(payload, dict):
        return None
    return CompositeTablePartLayout(
        kind=str(payload.get("kind") or ""),
        show_header=_as_optional_bool(get_value(payload, CompositeTablePartLayout, "show_header")),
        columns=[composite_table_column_from_dict(item) for item in list(payload.get("columns") or [])],
    )


def composite_table_part_layout_to_dict(layout: CompositeTablePartLayout) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kind": layout.kind,
    }
    if layout.show_header is not None:
        set_value(payload, CompositeTablePartLayout, "show_header", layout.show_header)
    if layout.columns:
        payload["columns"] = [composite_table_column_to_dict(item) for item in layout.columns]
    return payload


def summary_row_def_from_dict(payload: dict[str, Any]) -> SummaryRowDef:
    return SummaryRowDef(
        id=str(payload.get("id") or ""),
        title=str(payload.get("title") or ""),
    )


def summary_row_def_to_dict(row: SummaryRowDef) -> dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
    }


def summary_table_spec_from_dict(payload: Any) -> SummaryTableSpec | None:
    if not isinstance(payload, dict):
        return None
    return SummaryTableSpec(
        part_ids=[str(item) for item in list(get_value(payload, SummaryTableSpec, "part_ids") or [])],
        rows=[summary_row_def_from_dict(item) for item in list(payload.get("rows") or [])],
        prompt=_as_optional_str(payload.get("prompt")),
    )


def summary_table_spec_to_dict(spec: SummaryTableSpec) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "rows": [summary_row_def_to_dict(item) for item in spec.rows],
    }
    set_value(payload, SummaryTableSpec, "part_ids", list(spec.part_ids))
    if spec.prompt is not None:
        payload["prompt"] = spec.prompt
    return payload


def composite_table_part_from_dict(payload: dict[str, Any]) -> CompositeTablePart:
    return CompositeTablePart(
        id=str(payload.get("id") or ""),
        title=str(payload.get("title") or ""),
        source_type=str(get_value(payload, CompositeTablePart, "source_type") or ""),
        description=_as_optional_str(payload.get("description")),
        dataset_id=_as_optional_str(get_value(payload, CompositeTablePart, "dataset_id")),
        summary_spec=summary_table_spec_from_dict(get_value(payload, CompositeTablePart, "summary_spec")),
        table_layout=composite_table_part_layout_from_dict(get_value(payload, CompositeTablePart, "table_layout")),
    )


def composite_table_part_to_dict(part: CompositeTablePart) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": part.id,
        "title": part.title,
    }
    set_value(payload, CompositeTablePart, "source_type", part.source_type)
    if part.description is not None:
        payload["description"] = part.description
    if part.dataset_id is not None:
        set_value(payload, CompositeTablePart, "dataset_id", part.dataset_id)
    if part.summary_spec is not None:
        set_value(payload, CompositeTablePart, "summary_spec", summary_table_spec_to_dict(part.summary_spec))
    if part.table_layout is not None:
        set_value(payload, CompositeTablePart, "table_layout", composite_table_part_layout_to_dict(part.table_layout))
    return payload


def presentation_block_from_dict(payload: dict[str, Any]) -> PresentationBlock:
    return PresentationBlock(
        id=str(payload.get("id") or ""),
        type=str(payload.get("type") or ""),
        title=_as_optional_str(payload.get("title")),
        dataset_id=_as_optional_str(get_value(payload, PresentationBlock, "dataset_id")),
        description=_as_optional_str(payload.get("description")),
        parts=[composite_table_part_from_dict(item) for item in list(payload.get("parts") or [])],
    )


def presentation_block_to_dict(block: PresentationBlock) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": block.id,
        "type": block.type,
    }
    if block.title is not None:
        payload["title"] = block.title
    if block.dataset_id is not None:
        set_value(payload, PresentationBlock, "dataset_id", block.dataset_id)
    if block.description is not None:
        payload["description"] = block.description
    if block.parts:
        payload["parts"] = [composite_table_part_to_dict(item) for item in block.parts]
    return payload


def presentation_definition_from_dict(payload: dict[str, Any]) -> PresentationDefinition:
    return PresentationDefinition(
        kind=str(payload.get("kind") or ""),
        blocks=[presentation_block_from_dict(item) for item in list(payload.get("blocks") or [])],
    )


def presentation_definition_to_dict(presentation: PresentationDefinition) -> dict[str, Any]:
    return {
        "kind": presentation.kind,
        "blocks": [presentation_block_to_dict(item) for item in presentation.blocks],
    }


def section_content_definition_from_dict(payload: dict[str, Any]) -> SectionContentDefinition:
    return SectionContentDefinition(
        presentation=presentation_definition_from_dict(payload.get("presentation") or {}),
        datasets=[dataset_definition_from_dict(item) for item in list(payload.get("datasets") or [])],
    )


def section_content_definition_to_dict(content: SectionContentDefinition) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "presentation": presentation_definition_to_dict(content.presentation),
    }
    if content.datasets:
        payload["datasets"] = [dataset_definition_to_dict(item) for item in content.datasets]
    return payload


def section_definition_from_dict(payload: dict[str, Any]) -> SectionDefinition:
    return SectionDefinition(
        id=str(payload.get("id") or ""),
        outline=outline_definition_from_dict(payload.get("outline") or {}),
        content=section_content_definition_from_dict(payload.get("content") or {}),
        description=_as_optional_str(payload.get("description")),
        parameters=[parameter_from_dict(item) for item in list(payload.get("parameters") or [])],
        foreach=foreach_definition_from_dict(payload.get("foreach")),
    )


def section_definition_to_dict(section: SectionDefinition) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": section.id,
        "outline": outline_definition_to_dict(section.outline),
        "content": section_content_definition_to_dict(section.content),
    }
    if section.description is not None:
        payload["description"] = section.description
    if section.parameters:
        payload["parameters"] = [parameter_to_dict(item) for item in section.parameters]
    if section.foreach is not None:
        payload["foreach"] = foreach_definition_to_dict(section.foreach)
    return payload


def catalog_definition_from_dict(payload: dict[str, Any]) -> CatalogDefinition:
    return CatalogDefinition(
        id=str(payload.get("id") or ""),
        title=str(payload.get("title") or ""),
        description=_as_optional_str(payload.get("description")),
        parameters=[parameter_from_dict(item) for item in list(payload.get("parameters") or [])],
        foreach=foreach_definition_from_dict(payload.get("foreach")),
        sub_catalogs=[catalog_definition_from_dict(item) for item in list(get_value(payload, CatalogDefinition, "sub_catalogs") or [])],
        sections=[section_definition_from_dict(item) for item in list(payload.get("sections") or [])],
    )


def catalog_definition_to_dict(catalog: CatalogDefinition) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": catalog.id,
        "title": catalog.title,
    }
    if catalog.description is not None:
        payload["description"] = catalog.description
    if catalog.parameters:
        payload["parameters"] = [parameter_to_dict(item) for item in catalog.parameters]
    if catalog.foreach is not None:
        payload["foreach"] = foreach_definition_to_dict(catalog.foreach)
    if catalog.sub_catalogs:
        set_value(payload, CatalogDefinition, "sub_catalogs", [catalog_definition_to_dict(item) for item in catalog.sub_catalogs])
    if catalog.sections:
        payload["sections"] = [section_definition_to_dict(item) for item in catalog.sections]
    return payload


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


def _as_optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None
