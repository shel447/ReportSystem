"""纯领域辅助函数，用于推进模板实例并派生报告期结构。"""

from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from typing import Any

from ...template_catalog.domain.models import (
    CatalogDefinition,
    CompositeTablePart,
    DatasetDefinition,
    OutlineDefinition,
    Parameter,
    ParameterRuntimeContext,
    ParameterValue,
    PresentationBlock,
    ReportTemplate,
    RequirementItem,
    SectionDefinition,
    SectionContentDefinition,
    catalog_definition_from_dict,
    parameter_from_dict,
    report_template_from_dict,
)
from .models import (
    ExecutionBinding,
    ForeachContext,
    ParameterConfirmation,
    PartRuntimeContext,
    SectionRuntimeContext,
    TemplateInstance,
    TemplateInstanceCatalog,
    TemplateInstanceCompositeTablePart,
    TemplateInstancePresentationBlock,
    TemplateInstancePresentationDefinition,
    TemplateInstanceSection,
    TemplateInstanceSectionContent,
    WarningItem,
    template_instance_to_dict,
)

ITEM_PLACEHOLDER_PATTERN = re.compile(r"\{@([A-Za-z0-9_\-]+)(?:\.(label|value|query))?\}")
PARAMETER_PLACEHOLDER_PATTERN = re.compile(r"\{\$([A-Za-z0-9_\-]+)(?:\.(label|value|query))?\}")
SQL_EQUALS_PATTERN = re.compile(r"^\s*([A-Za-z0-9_.]+)\s*=\s*(.+?)\s*$")


def merge_parameter_values(
    *,
    parameter_definitions: list[Parameter],
    current_values: dict[str, list[ParameterValue]] | None,
    incoming_values: dict[str, list[ParameterValue]] | None,
) -> dict[str, list[ParameterValue]]:
    """把传入参数值与默认值合并成统一 ParameterValue 结构。"""
    merged = copy.deepcopy(current_values or {})
    incoming = incoming_values or {}
    for definition in parameter_definitions:
        param_id = definition.id.strip()
        if not param_id:
            continue
        if param_id in incoming and incoming[param_id] is not None:
            merged[param_id] = _normalize_parameter_value_list(incoming[param_id])
            continue
        if param_id not in merged and definition.default_value:
            merged[param_id] = _normalize_parameter_value_list(definition.default_value)
    return merged


def parameters_to_value_map(parameters: list[Parameter] | None) -> dict[str, list[ParameterValue]]:
    value_map: dict[str, list[ParameterValue]] = {}
    for parameter in list(parameters or []):
        if parameter.id.strip() and parameter.values:
            value_map[parameter.id.strip()] = _normalize_parameter_value_list(parameter.values)
    return value_map


def parameters_by_id(parameters: list[Parameter] | None) -> dict[str, Parameter]:
    return {
        parameter.id.strip(): copy.deepcopy(parameter)
        for parameter in list(parameters or [])
        if parameter.id.strip()
    }


def instantiate_template_instance(
    *,
    instance_id: str,
    template: ReportTemplate,
    conversation_id: str,
    chat_id: str | None,
    status: str,
    capture_stage: str,
    revision: int,
    parameter_values: dict[str, list[ParameterValue]],
    current_parameters: list[Parameter] | None = None,
    warnings: list[WarningItem] | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> TemplateInstance:
    """基于模板与当前参数值创建标准运行时聚合。"""
    template_model = copy.deepcopy(template)
    current_parameter_models = [copy.deepcopy(item) for item in list(current_parameters or [])]
    root_parameter_definitions = list(template_model.parameters)
    all_parameter_definitions = collect_template_parameters(template_model)
    all_current_parameters = collect_instance_parameters(parameters=current_parameter_models, catalogs=None)
    effective_values = merge_parameter_values(
        parameter_definitions=all_parameter_definitions,
        current_values=parameters_to_value_map(all_current_parameters),
        incoming_values={key: _normalize_parameter_value_list(value) for key, value in (parameter_values or {}).items()},
    )
    root_parameters = materialize_parameters(
        parameter_definitions=root_parameter_definitions,
        effective_values=effective_values,
        current_parameters=all_current_parameters,
    )
    catalogs = build_catalog_instances(
        template=template_model,
        root_parameters=root_parameters,
        effective_values=effective_values,
        current_parameters=all_current_parameters,
    )
    all_materialized_parameters = collect_instance_parameters(parameters=root_parameters, catalogs=catalogs)
    missing_parameter_ids = [
        parameter.id
        for parameter in all_materialized_parameters
        if parameter.required and not parameter.values
    ]
    now = datetime.now(timezone.utc).replace(microsecond=0)
    confirmation = ParameterConfirmation(
        missing_parameter_ids=missing_parameter_ids,
        confirmed=not missing_parameter_ids and capture_stage in {"confirm_params", "generate_report", "report_ready"},
        confirmed_at=_isoformat(updated_at or now) if not missing_parameter_ids and capture_stage in {"confirm_params", "generate_report", "report_ready"} else None,
    )
    return TemplateInstance(
        id=instance_id,
        schema_version="template-instance.vNext-draft",
        template_id=template_model.id,
        template=copy.deepcopy(template_model),
        conversation_id=conversation_id,
        chat_id=chat_id,
        status=status,
        capture_stage=capture_stage,
        revision=revision,
        parameters=root_parameters,
        parameter_confirmation=confirmation,
        catalogs=catalogs,
        warnings=[copy.deepcopy(item) for item in list(warnings or [])],
        created_at=created_at or now,
        updated_at=updated_at or now,
    )


def materialize_parameters(
    *,
    parameter_definitions: list[Parameter],
    effective_values: dict[str, list[ParameterValue]] | None = None,
    current_parameters: list[Parameter] | None = None,
) -> list[Parameter]:
    current_by_id = parameters_by_id(current_parameters)
    value_map = copy.deepcopy(effective_values or {})
    materialized: list[Parameter] = []
    for definition in list(parameter_definitions or []):
        current = current_by_id.get(definition.id) or Parameter(
            id=definition.id,
            label=definition.label,
            input_type=definition.input_type,
            required=definition.required,
            multi=definition.multi,
            interaction_mode=definition.interaction_mode,
        )
        values = _normalize_parameter_value_list(
            value_map.get(definition.id)
            or current.values
            or definition.default_value
        )
        options = _normalize_parameter_value_list(current.options or definition.options)
        runtime_context = copy.deepcopy(current.runtime_context)
        if runtime_context is None and values:
            runtime_context = ParameterRuntimeContext()
        if runtime_context is not None and values and not runtime_context.value_source:
            runtime_context.value_source = (
                "default"
                if values == _normalize_parameter_value_list(definition.default_value)
                else "user_input"
            )
        materialized.append(
            Parameter(
                id=definition.id,
                label=definition.label,
                description=definition.description,
                input_type=definition.input_type,
                required=definition.required,
                multi=definition.multi,
                interaction_mode=definition.interaction_mode,
                placeholder=definition.placeholder,
                default_value=_normalize_parameter_value_list(definition.default_value),
                options=options,
                values=values,
                runtime_context=runtime_context,
                source=definition.source,
            )
        )
    return materialized


def build_catalog_instances(
    *,
    template: ReportTemplate,
    root_parameters: list[Parameter],
    effective_values: dict[str, list[ParameterValue]],
    current_parameters: list[Parameter] | None,
) -> list[TemplateInstanceCatalog]:
    catalogs: list[TemplateInstanceCatalog] = []
    inherited_values = parameters_to_value_map(root_parameters)
    for catalog in template.catalogs:
        catalogs.extend(
            expand_catalog_instances(
                catalog=catalog,
                inherited_values=inherited_values,
                effective_values=effective_values,
                current_parameters=current_parameters,
            )
        )
    return catalogs


def expand_catalog_instances(
    *,
    catalog: CatalogDefinition,
    inherited_values: dict[str, list[ParameterValue]],
    effective_values: dict[str, list[ParameterValue]],
    current_parameters: list[Parameter] | None,
) -> list[TemplateInstanceCatalog]:
    foreach = catalog.foreach
    if foreach is None:
        return [
            build_catalog_instance(
                catalog=catalog,
                inherited_values=inherited_values,
                effective_values=effective_values,
                current_parameters=current_parameters,
                foreach_context=None,
            )
        ]

    values = list(inherited_values.get(foreach.parameter_id) or [])
    if not foreach.parameter_id or not values:
        return [
            build_catalog_instance(
                catalog=catalog,
                inherited_values=inherited_values,
                effective_values=effective_values,
                current_parameters=current_parameters,
                foreach_context=None,
            )
        ]

    expanded: list[TemplateInstanceCatalog] = []
    for value in values:
        scoped_values = copy.deepcopy(inherited_values)
        scoped_values[foreach.parameter_id] = [_normalize_parameter_value(value)]
        expanded.append(
            build_catalog_instance(
                catalog=catalog,
                inherited_values=scoped_values,
                effective_values=effective_values,
                current_parameters=current_parameters,
                foreach_context=ForeachContext(
                    parameter_id=foreach.parameter_id,
                    item_values=[_normalize_parameter_value(value)],
                ),
            )
        )
    return expanded


def build_catalog_instance(
    *,
    catalog: CatalogDefinition,
    inherited_values: dict[str, list[ParameterValue]],
    effective_values: dict[str, list[ParameterValue]],
    current_parameters: list[Parameter] | None,
    foreach_context: ForeachContext | None,
) -> TemplateInstanceCatalog:
    catalog_parameters = materialize_parameters(
        parameter_definitions=catalog.parameters,
        effective_values=effective_values,
        current_parameters=current_parameters,
    )
    visible_values = {**copy.deepcopy(inherited_values), **parameters_to_value_map(catalog_parameters)}
    sub_catalogs: list[TemplateInstanceCatalog] = []
    sections: list[TemplateInstanceSection] = []
    for sub_catalog in catalog.sub_catalogs:
        sub_catalogs.extend(
            expand_catalog_instances(
                catalog=sub_catalog,
                inherited_values=visible_values,
                effective_values=effective_values,
                current_parameters=current_parameters,
            )
        )
    for section in catalog.sections:
        sections.extend(
            expand_section_instances(
                section=section,
                inherited_values=visible_values,
                effective_values=effective_values,
                current_parameters=current_parameters,
            )
        )
    return TemplateInstanceCatalog(
        id=catalog.id,
        title=catalog.title,
        rendered_title=render_parameter_text(catalog.title, visible_values),
        description=catalog.description,
        parameters=catalog_parameters,
        foreach_context=foreach_context,
        sub_catalogs=sub_catalogs,
        sections=sections,
    )


def expand_section_instances(
    *,
    section: SectionDefinition,
    inherited_values: dict[str, list[ParameterValue]],
    effective_values: dict[str, list[ParameterValue]],
    current_parameters: list[Parameter] | None,
) -> list[TemplateInstanceSection]:
    foreach = section.foreach
    if foreach is None:
        return [
            build_section_instance(
                section=section,
                inherited_values=inherited_values,
                effective_values=effective_values,
                current_parameters=current_parameters,
                foreach_context=None,
            )
        ]

    values = list(inherited_values.get(foreach.parameter_id) or [])
    if not foreach.parameter_id or not values:
        return [
            build_section_instance(
                section=section,
                inherited_values=inherited_values,
                effective_values=effective_values,
                current_parameters=current_parameters,
                foreach_context=None,
            )
        ]

    expanded: list[TemplateInstanceSection] = []
    for value in values:
        scoped_values = copy.deepcopy(inherited_values)
        scoped_values[foreach.parameter_id] = [_normalize_parameter_value(value)]
        expanded.append(
            build_section_instance(
                section=section,
                inherited_values=scoped_values,
                effective_values=effective_values,
                current_parameters=current_parameters,
                foreach_context=ForeachContext(
                    parameter_id=foreach.parameter_id,
                    item_values=[_normalize_parameter_value(value)],
                ),
            )
        )
    return expanded


def build_section_instance(
    *,
    section: SectionDefinition,
    inherited_values: dict[str, list[ParameterValue]],
    effective_values: dict[str, list[ParameterValue]],
    current_parameters: list[Parameter] | None,
    foreach_context: ForeachContext | None,
) -> TemplateInstanceSection:
    section_parameters = materialize_parameters(
        parameter_definitions=section.parameters,
        effective_values=effective_values,
        current_parameters=current_parameters,
    )
    visible_values = {**copy.deepcopy(inherited_values), **parameters_to_value_map(section_parameters)}
    item_instances = [build_requirement_item_instance(item=item, visible_values=visible_values) for item in section.outline.items]
    item_lookup = {item.id: item for item in item_instances}
    rendered_requirement = render_requirement_text(
        section.outline.requirement,
        item_lookup,
        visible_values,
    )
    runtime_bindings = build_execution_bindings(section=section, item_instances=item_instances)
    return TemplateInstanceSection(
        id=section.id,
        description=section.description,
        parameters=section_parameters,
        foreach_context=foreach_context,
        outline=OutlineDefinition(
            requirement=section.outline.requirement,
            rendered_requirement=rendered_requirement,
            items=item_instances,
        ),
        content=materialize_section_content(section=section, runtime_bindings=runtime_bindings),
        runtime_context=SectionRuntimeContext(bindings=runtime_bindings),
        skeleton_status="reusable",
        user_edited=False,
    )


def materialize_section_content(
    *,
    section: SectionDefinition,
    runtime_bindings: list[ExecutionBinding],
) -> TemplateInstanceSectionContent:
    return TemplateInstanceSectionContent(
        datasets=[copy.deepcopy(dataset) for dataset in section.content.datasets],
        presentation=TemplateInstancePresentationDefinition(
            kind=section.content.presentation.kind or "mixed",
            blocks=[_materialize_presentation_block(block, runtime_bindings=runtime_bindings) for block in section.content.presentation.blocks],
        ),
    )


def _materialize_presentation_block(
    block: PresentationBlock,
    *,
    runtime_bindings: list[ExecutionBinding],
) -> TemplateInstancePresentationBlock:
    if block.type != "composite_table":
        return TemplateInstancePresentationBlock(
            id=block.id,
            type=block.type,
            title=block.title,
            dataset_id=block.dataset_id,
            description=block.description,
        )
    return TemplateInstancePresentationBlock(
        id=block.id,
        type=block.type,
        title=block.title,
        description=block.description,
        parts=[_materialize_composite_table_part(part, runtime_bindings=runtime_bindings) for part in block.parts],
    )


def _materialize_composite_table_part(
    part: CompositeTablePart,
    *,
    runtime_bindings: list[ExecutionBinding],
) -> TemplateInstanceCompositeTablePart:
    return TemplateInstanceCompositeTablePart(
        id=part.id,
        title=part.title,
        description=part.description,
        source_type=part.source_type,
        dataset_id=part.dataset_id,
        summary_spec=copy.deepcopy(part.summary_spec),
        table_layout=copy.deepcopy(part.table_layout),
        runtime_context=_build_part_runtime_context(part=part, runtime_bindings=runtime_bindings),
    )


def _build_part_runtime_context(
    *,
    part: CompositeTablePart,
    runtime_bindings: list[ExecutionBinding],
) -> PartRuntimeContext:
    if part.source_type == "summary":
        return PartRuntimeContext(
            status="pending",
            resolved_part_ids=list(part.summary_spec.part_ids if part.summary_spec else []),
            prompt=part.summary_spec.prompt if part.summary_spec else None,
        )
    dataset_id = part.dataset_id or ""
    resolved_queries = [
        binding.resolved_query.strip()
        for binding in runtime_bindings
        if binding.target_ref.startswith(f"{dataset_id}.") and (binding.resolved_query or "").strip()
    ]
    return PartRuntimeContext(
        status="pending",
        resolved_dataset_id=dataset_id,
        resolved_query=" AND ".join(f"({query})" for query in resolved_queries) if len(resolved_queries) > 1 else (resolved_queries[0] if resolved_queries else None),
    )


def build_requirement_item_instance(
    *,
    item: RequirementItem,
    visible_values: dict[str, list[ParameterValue]],
) -> RequirementItem:
    source_parameter_id = (item.source_parameter_id or "").strip()
    if source_parameter_id:
        resolved_values = _normalize_parameter_value_list(visible_values.get(source_parameter_id) or item.default_value)
        value_source = "parameter_ref"
    else:
        resolved_values = _normalize_parameter_value_list(item.default_value or item.values)
        value_source = "default" if resolved_values else "system_fill"
    return RequirementItem(
        id=item.id,
        label=item.label,
        kind=item.kind,
        required=item.required,
        multi=item.multi,
        description=item.description,
        source_parameter_id=item.source_parameter_id,
        widget=item.widget,
        default_value=_normalize_parameter_value_list(item.default_value),
        values=resolved_values,
        value_source=value_source,
    )


def build_execution_bindings(
    *,
    section: SectionDefinition,
    item_instances: list[RequirementItem],
) -> list[ExecutionBinding]:
    bindings: list[ExecutionBinding] = []
    for dataset in section.content.datasets:
        for item in item_instances:
            values = _normalize_parameter_value_list(item.values)
            bindings.append(
                ExecutionBinding(
                    id=f"binding_{dataset.id}_{item.id}",
                    binding_type="dataset_parameter",
                    source_type=dataset.source_type or "sql",
                    target_ref=f"{dataset.id}.{item.id}",
                    multi_value_query_mode="single" if len(values) <= 1 else _default_multi_value_query_mode(values),
                    resolved_query=build_resolved_query(values),
                )
            )
    return bindings


def render_requirement_text(
    template_text: str,
    item_lookup: dict[str, RequirementItem],
    parameter_values: dict[str, list[ParameterValue]],
) -> str:
    rendered = ITEM_PLACEHOLDER_PATTERN.sub(lambda match: _render_item_placeholder(match, item_lookup), template_text)
    rendered = PARAMETER_PLACEHOLDER_PATTERN.sub(lambda match: _render_parameter_placeholder(match, parameter_values), rendered)
    return rendered.strip()


def render_parameter_text(template_text: str, parameter_values: dict[str, list[ParameterValue]]) -> str:
    rendered = PARAMETER_PLACEHOLDER_PATTERN.sub(lambda match: _render_parameter_placeholder(match, parameter_values), template_text)
    return rendered.strip()


def serialize_template_instance(instance: TemplateInstance) -> dict[str, Any]:
    return template_instance_to_dict(instance)


def collect_template_parameters(template: ReportTemplate) -> list[Parameter]:
    template_model = copy.deepcopy(template)
    parameters: list[Parameter] = [copy.deepcopy(item) for item in template_model.parameters]
    for catalog in template_model.catalogs:
        parameters.extend(_collect_catalog_template_parameters(catalog))
    return parameters


def _collect_catalog_template_parameters(catalog: CatalogDefinition) -> list[Parameter]:
    parameters: list[Parameter] = [copy.deepcopy(item) for item in catalog.parameters]
    for section in catalog.sections:
        parameters.extend(copy.deepcopy(section.parameters))
    for sub_catalog in catalog.sub_catalogs:
        parameters.extend(_collect_catalog_template_parameters(sub_catalog))
    return parameters


def collect_instance_parameters(
    *,
    parameters: list[Parameter] | None,
    catalogs: list[TemplateInstanceCatalog] | None,
) -> list[Parameter]:
    collected = copy.deepcopy(list(parameters or []))
    for catalog in list(catalogs or []):
        collected.extend(_collect_catalog_instance_parameters(catalog))
    return collected


def _collect_catalog_instance_parameters(catalog: TemplateInstanceCatalog) -> list[Parameter]:
    collected = copy.deepcopy(list(catalog.parameters))
    for section in catalog.sections:
        collected.extend(copy.deepcopy(section.parameters))
    for sub_catalog in catalog.sub_catalogs:
        collected.extend(_collect_catalog_instance_parameters(sub_catalog))
    return collected


def _render_item_placeholder(match: re.Match[str], item_lookup: dict[str, RequirementItem]) -> str:
    item_id = match.group(1)
    channel = match.group(2) or "label"
    item = item_lookup.get(item_id)
    if item is None:
        return ""
    return _render_value_channel(item.values, channel)


def _render_parameter_placeholder(match: re.Match[str], parameter_values: dict[str, list[ParameterValue]]) -> str:
    parameter_id = match.group(1)
    channel = match.group(2) or "label"
    return _render_value_channel(_normalize_parameter_value_list(parameter_values.get(parameter_id) or []), channel)


def _render_value_channel(values: list[ParameterValue], channel: str) -> str:
    rendered = [str(getattr(value, channel, None) or value.label or "") for value in values]
    return "、".join([text for text in rendered if text])


def build_resolved_query(values: list[ParameterValue]) -> str:
    queries = [str(value.query or "").strip() for value in values if str(value.query or "").strip()]
    if not queries:
        return ""
    if len(queries) == 1:
        return queries[0]
    parsed = [_parse_sql_equals(query) for query in queries]
    if parsed and all(item is not None for item in parsed):
        left = parsed[0][0]
        if all(item[0] == left for item in parsed):
            return f"{left} IN ({', '.join(item[1] for item in parsed)})"
    return " OR ".join(f"({query})" for query in queries)


def _default_multi_value_query_mode(values: list[ParameterValue]) -> str:
    queries = [str(value.query or "").strip() for value in values if str(value.query or "").strip()]
    if len(queries) <= 1:
        return "single"
    parsed = [_parse_sql_equals(query) for query in queries]
    if parsed and all(item is not None for item in parsed) and len({item[0] for item in parsed}) == 1:
        return "in"
    return "or"


def _parse_sql_equals(query: str) -> tuple[str, str] | None:
    matched = SQL_EQUALS_PATTERN.match(query)
    if not matched:
        return None
    return matched.group(1), matched.group(2)


def _normalize_parameter_value_list(values: Any) -> list[ParameterValue]:
    if isinstance(values, list):
        normalized: list[ParameterValue] = []
        for value in values:
            normalized_value = _normalize_parameter_value(value)
            if normalized_value is not None:
                normalized.append(normalized_value)
        return normalized
    return []


def _normalize_parameter_value(value: Any) -> ParameterValue | None:
    if isinstance(value, ParameterValue):
        return copy.deepcopy(value)
    if isinstance(value, dict) and {"label", "value", "query"}.issubset(value.keys()):
        return ParameterValue(
            label=value.get("label"),
            value=value.get("value"),
            query=value.get("query"),
        )
    return None


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")
