"""静态报告模板目录及其递归属性的领域模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypeVar

Scalar = str | int | float | bool


@dataclass(slots=True)
class ParameterValue:
    """参数值三通道。"""

    label: Scalar
    value: Scalar
    query: Scalar


@dataclass(slots=True)
class ParameterRuntimeContext:
    """参数运行时上下文。"""

    value_source: str | None = None
    query_context: dict[str, Any] | None = None
    confirmed: bool | None = None
    confirmed_at: str | None = None
    option_source: str | None = None
    options_fetched_at: str | None = None


@dataclass(slots=True)
class Parameter:
    """模板与模板实例共用的参数定义。"""

    id: str
    label: str
    input_type: str
    required: bool
    multi: bool
    interaction_mode: str
    description: str | None = None
    placeholder: str | None = None
    default_value: list[ParameterValue] = field(default_factory=list)
    options: list[ParameterValue] = field(default_factory=list)
    values: list[ParameterValue] = field(default_factory=list)
    runtime_context: ParameterRuntimeContext | None = None
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
    source_parameter_id: str | None = None
    widget: str | None = None
    default_value: list[ParameterValue] = field(default_factory=list)
    values: list[ParameterValue] = field(default_factory=list)
    value_source: str | None = None


@dataclass(slots=True)
class OutlineDefinition:
    """章节诉求定义。"""

    requirement: str
    items: list[RequirementItem] = field(default_factory=list)
    rendered_requirement: str | None = None


@dataclass(slots=True)
class ForeachDefinition:
    """模板级 foreach 定义。"""

    parameter_id: str
    alias: str


@dataclass(slots=True)
class DatasetDefinition:
    """章节数据集定义。"""

    id: str
    source_type: str
    source_ref: str
    name: str | None = None
    depends_on: list[str] = field(default_factory=list)
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
    show_header: bool | None = None
    columns: list[CompositeTableColumn] = field(default_factory=list)


@dataclass(slots=True)
class SummaryRowDef:
    """摘要行定义。"""

    id: str
    title: str


@dataclass(slots=True)
class SummaryTableSpec:
    """摘要分片定义。"""

    part_ids: list[str] = field(default_factory=list)
    rows: list[SummaryRowDef] = field(default_factory=list)
    prompt: str | None = None


@dataclass(slots=True)
class CompositeTablePart:
    """复合表分片定义。"""

    id: str
    title: str
    source_type: str
    description: str | None = None
    dataset_id: str | None = None
    summary_spec: SummaryTableSpec | None = None
    table_layout: CompositeTablePartLayout | None = None


@dataclass(slots=True)
class PresentationBlock:
    """章节展示块定义。"""

    id: str
    type: str
    title: str | None = None
    dataset_id: str | None = None
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
    sub_catalogs: list["CatalogDefinition"] = field(default_factory=list)
    sections: list[SectionDefinition] = field(default_factory=list)


@dataclass(slots=True)
class ReportTemplate:
    """模板目录与运行时共用的正式静态模板聚合。"""

    id: str
    category: str
    name: str
    description: str
    schema_version: str
    parameters: list[Parameter] = field(default_factory=list)
    catalogs: list[CatalogDefinition] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class TemplateSummary:
    """用于列表页和轻量选择器的紧凑投影。"""

    id: str
    category: str
    name: str
    description: str
    schema_version: str
    updated_at: datetime | None = None


@dataclass(slots=True)
class TemplateMatchCandidate:
    """当模板排序外置时使用的语义匹配候选投影。"""

    template_id: str
    template_name: str
    category: str
    description: str
    score: float
    reasons: list[str] = field(default_factory=list)


T = TypeVar("T")


def report_template_from_dict(payload: dict[str, Any]) -> ReportTemplate:
    """把模板 JSON 契约转换为领域 dataclass。"""
    return ReportTemplate(
        id=str(payload.get("id") or ""),
        category=str(payload.get("category") or ""),
        name=str(payload.get("name") or ""),
        description=str(payload.get("description") or ""),
        schema_version=str(payload.get("schemaVersion") or ""),
        parameters=[parameter_from_dict(item) for item in list(payload.get("parameters") or [])],
        catalogs=[catalog_definition_from_dict(item) for item in list(payload.get("catalogs") or [])],
        tags=[str(item) for item in list(payload.get("tags") or [])],
        created_at=_as_datetime(payload.get("createdAt")),
        updated_at=_as_datetime(payload.get("updatedAt")),
    )


def report_template_to_dict(template: ReportTemplate) -> dict[str, Any]:
    """把模板领域对象投影为公开 JSON 契约。"""
    return {
        "id": template.id,
        "category": template.category,
        "name": template.name,
        "description": template.description,
        "schemaVersion": template.schema_version,
        "tags": list(template.tags),
        "parameters": [parameter_to_dict(item) for item in template.parameters],
        "catalogs": [catalog_definition_to_dict(item) for item in template.catalogs],
        "createdAt": _isoformat(template.created_at),
        "updatedAt": _isoformat(template.updated_at),
    }


def parameter_from_dict(payload: dict[str, Any]) -> Parameter:
    return Parameter(
        id=str(payload.get("id") or ""),
        label=str(payload.get("label") or ""),
        input_type=str(payload.get("inputType") or ""),
        required=bool(payload.get("required")),
        multi=bool(payload.get("multi")),
        interaction_mode=str(payload.get("interactionMode") or ""),
        description=_as_optional_str(payload.get("description")),
        placeholder=_as_optional_str(payload.get("placeholder")),
        default_value=[parameter_value_from_dict(item) for item in list(payload.get("defaultValue") or [])],
        options=[parameter_value_from_dict(item) for item in list(payload.get("options") or [])],
        values=[parameter_value_from_dict(item) for item in list(payload.get("values") or [])],
        runtime_context=parameter_runtime_context_from_dict(payload.get("runtimeContext")),
        source=_as_optional_str(payload.get("source")),
    )


def parameter_to_dict(parameter: Parameter) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": parameter.id,
        "label": parameter.label,
        "inputType": parameter.input_type,
        "required": parameter.required,
        "multi": parameter.multi,
        "interactionMode": parameter.interaction_mode,
    }
    if parameter.description is not None:
        payload["description"] = parameter.description
    if parameter.placeholder is not None:
        payload["placeholder"] = parameter.placeholder
    if parameter.default_value:
        payload["defaultValue"] = [parameter_value_to_dict(item) for item in parameter.default_value]
    if parameter.options or parameter.input_type == "enum":
        payload["options"] = [parameter_value_to_dict(item) for item in parameter.options]
    if parameter.values:
        payload["values"] = [parameter_value_to_dict(item) for item in parameter.values]
    if parameter.runtime_context is not None:
        payload["runtimeContext"] = parameter_runtime_context_to_dict(parameter.runtime_context)
    if parameter.source is not None:
        payload["source"] = parameter.source
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
        value_source=_as_optional_str(payload.get("valueSource")),
        query_context=dict(payload.get("queryContext") or {}) or None,
        confirmed=_as_optional_bool(payload.get("confirmed")),
        confirmed_at=_as_optional_str(payload.get("confirmedAt")),
        option_source=_as_optional_str(payload.get("optionSource")),
        options_fetched_at=_as_optional_str(payload.get("optionsFetchedAt")),
    )


def parameter_runtime_context_to_dict(context: ParameterRuntimeContext) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if context.value_source is not None:
        payload["valueSource"] = context.value_source
    if context.query_context is not None:
        payload["queryContext"] = dict(context.query_context)
    if context.confirmed is not None:
        payload["confirmed"] = context.confirmed
    if context.confirmed_at is not None:
        payload["confirmedAt"] = context.confirmed_at
    if context.option_source is not None:
        payload["optionSource"] = context.option_source
    if context.options_fetched_at is not None:
        payload["optionsFetchedAt"] = context.options_fetched_at
    return payload


def requirement_item_from_dict(payload: dict[str, Any]) -> RequirementItem:
    return RequirementItem(
        id=str(payload.get("id") or ""),
        label=str(payload.get("label") or ""),
        kind=str(payload.get("kind") or ""),
        required=bool(payload.get("required")),
        multi=bool(payload.get("multi")) if payload.get("multi") is not None else False,
        description=_as_optional_str(payload.get("description")),
        source_parameter_id=_as_optional_str(payload.get("sourceParameterId")),
        widget=_as_optional_str(payload.get("widget")),
        default_value=[parameter_value_from_dict(item) for item in list(payload.get("defaultValue") or [])],
        values=[parameter_value_from_dict(item) for item in list(payload.get("values") or [])],
        value_source=_as_optional_str(payload.get("valueSource")),
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
        payload["sourceParameterId"] = item.source_parameter_id
    if item.widget is not None:
        payload["widget"] = item.widget
    if item.default_value:
        payload["defaultValue"] = [parameter_value_to_dict(value) for value in item.default_value]
    if item.values:
        payload["values"] = [parameter_value_to_dict(value) for value in item.values]
    if item.value_source is not None:
        payload["valueSource"] = item.value_source
    return payload


def outline_definition_from_dict(payload: dict[str, Any]) -> OutlineDefinition:
    return OutlineDefinition(
        requirement=str(payload.get("requirement") or ""),
        rendered_requirement=_as_optional_str(payload.get("renderedRequirement")),
        items=[requirement_item_from_dict(item) for item in list(payload.get("items") or [])],
    )


def outline_definition_to_dict(outline: OutlineDefinition) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "requirement": outline.requirement,
        "items": [requirement_item_to_dict(item) for item in outline.items],
    }
    if outline.rendered_requirement is not None:
        payload["renderedRequirement"] = outline.rendered_requirement
    return payload


def foreach_definition_from_dict(payload: Any) -> ForeachDefinition | None:
    if not isinstance(payload, dict):
        return None
    return ForeachDefinition(
        parameter_id=str(payload.get("parameterId") or ""),
        alias=str(payload.get("as") or ""),
    )


def foreach_definition_to_dict(foreach: ForeachDefinition) -> dict[str, Any]:
    return {
        "parameterId": foreach.parameter_id,
        "as": foreach.alias,
    }


def dataset_definition_from_dict(payload: dict[str, Any]) -> DatasetDefinition:
    return DatasetDefinition(
        id=str(payload.get("id") or ""),
        source_type=str(payload.get("sourceType") or ""),
        source_ref=str(payload.get("sourceRef") or ""),
        name=_as_optional_str(payload.get("name")),
        depends_on=[str(item) for item in list(payload.get("dependsOn") or [])],
        description=_as_optional_str(payload.get("description")),
    )


def dataset_definition_to_dict(dataset: DatasetDefinition) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": dataset.id,
        "sourceType": dataset.source_type,
        "sourceRef": dataset.source_ref,
    }
    if dataset.name is not None:
        payload["name"] = dataset.name
    if dataset.depends_on:
        payload["dependsOn"] = list(dataset.depends_on)
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
        show_header=_as_optional_bool(payload.get("showHeader")),
        columns=[composite_table_column_from_dict(item) for item in list(payload.get("columns") or [])],
    )


def composite_table_part_layout_to_dict(layout: CompositeTablePartLayout) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kind": layout.kind,
    }
    if layout.show_header is not None:
        payload["showHeader"] = layout.show_header
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
        part_ids=[str(item) for item in list(payload.get("partIds") or [])],
        rows=[summary_row_def_from_dict(item) for item in list(payload.get("rows") or [])],
        prompt=_as_optional_str(payload.get("prompt")),
    )


def summary_table_spec_to_dict(spec: SummaryTableSpec) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "partIds": list(spec.part_ids),
        "rows": [summary_row_def_to_dict(item) for item in spec.rows],
    }
    if spec.prompt is not None:
        payload["prompt"] = spec.prompt
    return payload


def composite_table_part_from_dict(payload: dict[str, Any]) -> CompositeTablePart:
    return CompositeTablePart(
        id=str(payload.get("id") or ""),
        title=str(payload.get("title") or ""),
        source_type=str(payload.get("sourceType") or ""),
        description=_as_optional_str(payload.get("description")),
        dataset_id=_as_optional_str(payload.get("datasetId")),
        summary_spec=summary_table_spec_from_dict(payload.get("summarySpec")),
        table_layout=composite_table_part_layout_from_dict(payload.get("tableLayout")),
    )


def composite_table_part_to_dict(part: CompositeTablePart) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": part.id,
        "title": part.title,
        "sourceType": part.source_type,
    }
    if part.description is not None:
        payload["description"] = part.description
    if part.dataset_id is not None:
        payload["datasetId"] = part.dataset_id
    if part.summary_spec is not None:
        payload["summarySpec"] = summary_table_spec_to_dict(part.summary_spec)
    if part.table_layout is not None:
        payload["tableLayout"] = composite_table_part_layout_to_dict(part.table_layout)
    return payload


def presentation_block_from_dict(payload: dict[str, Any]) -> PresentationBlock:
    return PresentationBlock(
        id=str(payload.get("id") or ""),
        type=str(payload.get("type") or ""),
        title=_as_optional_str(payload.get("title")),
        dataset_id=_as_optional_str(payload.get("datasetId")),
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
        payload["datasetId"] = block.dataset_id
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
        sub_catalogs=[catalog_definition_from_dict(item) for item in list(payload.get("subCatalogs") or [])],
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
        payload["subCatalogs"] = [catalog_definition_to_dict(item) for item in catalog.sub_catalogs]
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
