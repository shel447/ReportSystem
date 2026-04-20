"""纯领域辅助函数，用于推进模板实例并派生报告期结构。"""

from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from typing import Any

from .models import TemplateInstance

ITEM_PLACEHOLDER_PATTERN = re.compile(r"\{@([A-Za-z0-9_\-]+)(?:\.(label|value|query))?\}")
PARAMETER_PLACEHOLDER_PATTERN = re.compile(r"\{\$([A-Za-z0-9_\-]+)(?:\.(label|value|query))?\}")
SQL_EQUALS_PATTERN = re.compile(r"^\s*([A-Za-z0-9_.]+)\s*=\s*(.+?)\s*$")


def merge_parameter_values(
    *,
    parameter_definitions: list[dict[str, Any]],
    current_values: dict[str, list[dict[str, Any]]] | None,
    incoming_values: dict[str, list[dict[str, Any]]] | None,
) -> dict[str, list[dict[str, Any]]]:
    """把传入参数值与默认值合并成统一 ParameterValue 结构。"""
    merged = copy.deepcopy(current_values or {})
    incoming = incoming_values or {}
    for definition in parameter_definitions:
        param_id = str(definition.get("id") or "").strip()
        if not param_id:
            continue
        if param_id in incoming and incoming[param_id] is not None:
            merged[param_id] = _normalize_parameter_value_list(incoming[param_id])
            continue
        if param_id not in merged:
            default_value = definition.get("defaultValue")
            if isinstance(default_value, list):
                merged[param_id] = _normalize_parameter_value_list(default_value)
    return merged


def parameters_to_value_map(parameters: list[dict[str, Any]] | None) -> dict[str, list[dict[str, Any]]]:
    value_map: dict[str, list[dict[str, Any]]] = {}
    for parameter in list(parameters or []):
        param_id = str(parameter.get("id") or "").strip()
        if not param_id:
            continue
        values = _normalize_parameter_value_list(parameter.get("values") or [])
        if values:
            value_map[param_id] = values
    return value_map


def parameters_by_id(parameters: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    return {
        str(parameter.get("id") or "").strip(): copy.deepcopy(parameter)
        for parameter in list(parameters or [])
        if str(parameter.get("id") or "").strip()
    }


def instantiate_template_instance(
    *,
    instance_id: str,
    template: dict[str, Any],
    conversation_id: str,
    chat_id: str | None,
    status: str,
    capture_stage: str,
    revision: int,
    parameter_values: dict[str, list[dict[str, Any]]],
    current_parameters: list[dict[str, Any]] | None = None,
    warnings: list[dict[str, Any]] | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> TemplateInstance:
    """基于模板与当前参数值创建标准运行时聚合。"""
    root_parameter_definitions = list(template.get("parameters") or [])
    all_parameter_definitions = collect_template_parameters(template)
    all_current_parameters = collect_instance_parameters(
        parameters=current_parameters,
        catalogs=None,
    )
    effective_values = merge_parameter_values(
        parameter_definitions=all_parameter_definitions,
        current_values=parameters_to_value_map(all_current_parameters),
        incoming_values=parameter_values,
    )
    root_parameters = materialize_parameters(
        parameter_definitions=root_parameter_definitions,
        effective_values=effective_values,
        current_parameters=all_current_parameters,
    )
    catalogs = build_catalog_instances(
        template=template,
        root_parameters=root_parameters,
        effective_values=effective_values,
        current_parameters=all_current_parameters,
    )
    all_materialized_parameters = collect_instance_parameters(parameters=root_parameters, catalogs=catalogs)
    missing_parameter_ids = [
        str(parameter.get("id") or "")
        for parameter in all_materialized_parameters
        if parameter.get("required") and not list(parameter.get("values") or [])
    ]
    now = datetime.now(timezone.utc).replace(microsecond=0)
    confirmation = {
        "missingParameterIds": missing_parameter_ids,
        "confirmed": not missing_parameter_ids and capture_stage in {"confirm_params", "generate_report", "report_ready"},
    }
    if confirmation["confirmed"]:
        confirmation["confirmedAt"] = _isoformat(updated_at or now)

    return TemplateInstance(
        id=instance_id,
        schema_version="template-instance.vNext-draft",
        template_id=str(template.get("id") or ""),
        template=copy.deepcopy(template),
        conversation_id=conversation_id,
        chat_id=chat_id,
        status=status,
        capture_stage=capture_stage,
        revision=revision,
        parameters=root_parameters,
        parameter_confirmation=confirmation,
        catalogs=catalogs,
        warnings=list(warnings or []),
        created_at=created_at or now,
        updated_at=updated_at or now,
    )


def materialize_parameters(
    *,
    parameter_definitions: list[dict[str, Any]],
    effective_values: dict[str, list[dict[str, Any]]] | None = None,
    current_parameters: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    current_by_id = parameters_by_id(current_parameters)
    value_map = copy.deepcopy(effective_values or {})
    materialized: list[dict[str, Any]] = []
    for definition in list(parameter_definitions or []):
        param_id = str(definition.get("id") or "").strip()
        if not param_id:
            continue
        current = current_by_id.get(param_id) or {}
        values = _normalize_parameter_value_list(value_map.get(param_id) or current.get("values") or definition.get("defaultValue") or [])
        options = _normalize_parameter_value_list(current.get("options") or definition.get("options") or [])
        runtime_context = copy.deepcopy(current.get("runtimeContext") or {})
        if values and not runtime_context.get("valueSource"):
            runtime_context["valueSource"] = "default" if values == _normalize_parameter_value_list(definition.get("defaultValue") or []) else "user_input"
        materialized_parameter = {
            "id": param_id,
            "label": definition.get("label"),
            "description": definition.get("description"),
            "inputType": definition.get("inputType"),
            "required": bool(definition.get("required")),
            "multi": bool(definition.get("multi")),
            "interactionMode": definition.get("interactionMode"),
        }
        if definition.get("placeholder") is not None:
            materialized_parameter["placeholder"] = definition.get("placeholder")
        if isinstance(definition.get("defaultValue"), list):
            materialized_parameter["defaultValue"] = _normalize_parameter_value_list(definition.get("defaultValue"))
        if isinstance(definition.get("source"), str) and definition.get("source"):
            materialized_parameter["source"] = definition.get("source")
        if options or definition.get("inputType") == "enum":
            materialized_parameter["options"] = options
        if values:
            materialized_parameter["values"] = values
        if runtime_context:
            materialized_parameter["runtimeContext"] = runtime_context
        materialized.append(materialized_parameter)
    return materialized


def build_catalog_instances(
    *,
    template: dict[str, Any],
    root_parameters: list[dict[str, Any]],
    effective_values: dict[str, list[dict[str, Any]]],
    current_parameters: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    catalogs: list[dict[str, Any]] = []
    inherited_values = parameters_to_value_map(root_parameters)
    for catalog in list(template.get("catalogs") or []):
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
    catalog: dict[str, Any],
    inherited_values: dict[str, list[dict[str, Any]]],
    effective_values: dict[str, list[dict[str, Any]]],
    current_parameters: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    foreach = catalog.get("foreach") if isinstance(catalog.get("foreach"), dict) else None
    if not foreach:
        return [
            build_catalog_instance(
                catalog=catalog,
                inherited_values=inherited_values,
                effective_values=effective_values,
                current_parameters=current_parameters,
                foreach_context=None,
            )
        ]

    parameter_id = str(foreach.get("parameterId") or "").strip()
    values = list(inherited_values.get(parameter_id) or [])
    if not parameter_id or not values:
        return [build_catalog_instance(catalog=catalog, inherited_values=inherited_values, foreach_context=None)]

    expanded: list[dict[str, Any]] = []
    for value in values:
        scoped_values = copy.deepcopy(inherited_values)
        scoped_values[parameter_id] = [_normalize_parameter_value(value)]
        expanded.append(
            build_catalog_instance(
                catalog=catalog,
                inherited_values=scoped_values,
                effective_values=effective_values,
                current_parameters=current_parameters,
                foreach_context={
                    "parameterId": parameter_id,
                    "itemValues": [_normalize_parameter_value(value)],
                },
            )
        )
    return expanded


def build_catalog_instance(
    *,
    catalog: dict[str, Any],
    inherited_values: dict[str, list[dict[str, Any]]],
    effective_values: dict[str, list[dict[str, Any]]],
    current_parameters: list[dict[str, Any]] | None,
    foreach_context: dict[str, Any] | None,
) -> dict[str, Any]:
    catalog_parameters = materialize_parameters(
        parameter_definitions=list(catalog.get("parameters") or []),
        effective_values=effective_values,
        current_parameters=current_parameters,
    )
    visible_values = {**copy.deepcopy(inherited_values), **parameters_to_value_map(catalog_parameters)}
    built: dict[str, Any] = {
        "id": catalog.get("id"),
        "title": catalog.get("title"),
        "renderedTitle": render_parameter_text(str(catalog.get("title") or ""), visible_values),
    }
    if catalog.get("description") is not None:
        built["description"] = catalog.get("description")
    if catalog_parameters:
        built["parameters"] = catalog_parameters
    if foreach_context:
        built["foreachContext"] = foreach_context

    sub_catalogs = []
    for sub_catalog in list(catalog.get("subCatalogs") or []):
        sub_catalogs.extend(
            expand_catalog_instances(
                catalog=sub_catalog,
                inherited_values=visible_values,
                effective_values=effective_values,
                current_parameters=current_parameters,
            )
        )
    sections = []
    for section in list(catalog.get("sections") or []):
        sections.extend(
            expand_section_instances(
                section=section,
                inherited_values=visible_values,
                effective_values=effective_values,
                current_parameters=current_parameters,
            )
        )
    if sub_catalogs:
        built["subCatalogs"] = sub_catalogs
    if sections:
        built["sections"] = sections
    return built


def expand_section_instances(
    *,
    section: dict[str, Any],
    inherited_values: dict[str, list[dict[str, Any]]],
    effective_values: dict[str, list[dict[str, Any]]],
    current_parameters: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    foreach = section.get("foreach") if isinstance(section.get("foreach"), dict) else None
    if not foreach:
        return [
            build_section_instance(
                section=section,
                inherited_values=inherited_values,
                effective_values=effective_values,
                current_parameters=current_parameters,
                foreach_context=None,
            )
        ]

    parameter_id = str(foreach.get("parameterId") or "").strip()
    values = list(inherited_values.get(parameter_id) or [])
    if not parameter_id or not values:
        return [build_section_instance(section=section, inherited_values=inherited_values, foreach_context=None)]

    expanded: list[dict[str, Any]] = []
    for value in values:
        scoped_values = copy.deepcopy(inherited_values)
        scoped_values[parameter_id] = [_normalize_parameter_value(value)]
        expanded.append(
            build_section_instance(
                section=section,
                inherited_values=scoped_values,
                effective_values=effective_values,
                current_parameters=current_parameters,
                foreach_context={
                    "parameterId": parameter_id,
                    "itemValues": [_normalize_parameter_value(value)],
                },
            )
        )
    return expanded


def build_section_instance(
    *,
    section: dict[str, Any],
    inherited_values: dict[str, list[dict[str, Any]]],
    effective_values: dict[str, list[dict[str, Any]]],
    current_parameters: list[dict[str, Any]] | None,
    foreach_context: dict[str, Any] | None,
) -> dict[str, Any]:
    section_parameters = materialize_parameters(
        parameter_definitions=list(section.get("parameters") or []),
        effective_values=effective_values,
        current_parameters=current_parameters,
    )
    visible_values = {**copy.deepcopy(inherited_values), **parameters_to_value_map(section_parameters)}
    outline = section.get("outline") if isinstance(section.get("outline"), dict) else {}
    item_instances = [
        build_requirement_item_instance(item=item, visible_values=visible_values)
        for item in list(outline.get("items") or [])
    ]
    item_lookup = {item["id"]: item for item in item_instances}
    rendered_requirement = render_requirement_text(str(outline.get("requirement") or ""), item_lookup, visible_values)
    built: dict[str, Any] = {
        "id": section.get("id"),
        "outline": {
            "requirement": str(outline.get("requirement") or ""),
            "renderedRequirement": rendered_requirement,
            "items": item_instances,
        },
        "runtimeContext": {
            "bindings": build_execution_bindings(section=section, item_instances=item_instances),
        },
        "skeletonStatus": "reusable",
        "userEdited": False,
    }
    if section.get("description") is not None:
        built["description"] = section.get("description")
    if section_parameters:
        built["parameters"] = section_parameters
    if foreach_context:
        built["foreachContext"] = foreach_context
    return built


def build_requirement_item_instance(*, item: dict[str, Any], visible_values: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    source_parameter_id = str(item.get("sourceParameterId") or "").strip()
    if source_parameter_id:
        resolved_values = _normalize_parameter_value_list(visible_values.get(source_parameter_id) or item.get("defaultValue") or [])
        value_source = "parameter_ref"
    else:
        resolved_values = _normalize_parameter_value_list(item.get("defaultValue") or item.get("values") or [])
        value_source = "default" if resolved_values else "system_fill"
    built = {
        "id": item.get("id"),
        "label": item.get("label"),
        "kind": item.get("kind"),
        "required": bool(item.get("required")),
    }
    if item.get("multi") is not None:
        built["multi"] = bool(item.get("multi"))
    if item.get("description") is not None:
        built["description"] = item.get("description")
    if source_parameter_id:
        built["sourceParameterId"] = source_parameter_id
    if item.get("widget") is not None:
        built["widget"] = item.get("widget")
    if isinstance(item.get("defaultValue"), list):
        built["defaultValue"] = _normalize_parameter_value_list(item.get("defaultValue"))
    if resolved_values:
        built["values"] = resolved_values
    built["valueSource"] = value_source
    return built


def build_execution_bindings(*, section: dict[str, Any], item_instances: list[dict[str, Any]]) -> list[dict[str, Any]]:
    datasets = ((section.get("content") or {}).get("datasets") or []) if isinstance(section.get("content"), dict) else []
    bindings: list[dict[str, Any]] = []
    for dataset in datasets:
        dataset_id = str(dataset.get("id") or "")
        for item in item_instances:
            values = _normalize_parameter_value_list(item.get("values") or [])
            bindings.append(
                {
                    "id": f"binding_{dataset_id}_{item.get('id')}",
                    "bindingType": "dataset_parameter",
                    "sourceType": dataset.get("sourceType") or "sql",
                    "targetRef": f"{dataset_id}.{item.get('id')}",
                    "multiValueQueryMode": "single" if len(values) <= 1 else _default_multi_value_query_mode(values),
                    "resolvedQuery": build_resolved_query(values),
                }
            )
    return bindings


def render_requirement_text(template_text: str, item_lookup: dict[str, dict[str, Any]], parameter_values: dict[str, list[dict[str, Any]]]) -> str:
    rendered = ITEM_PLACEHOLDER_PATTERN.sub(lambda match: _render_item_placeholder(match, item_lookup), template_text)
    rendered = PARAMETER_PLACEHOLDER_PATTERN.sub(lambda match: _render_parameter_placeholder(match, parameter_values), rendered)
    return rendered.strip()


def render_parameter_text(template_text: str, parameter_values: dict[str, list[dict[str, Any]]]) -> str:
    rendered = PARAMETER_PLACEHOLDER_PATTERN.sub(lambda match: _render_parameter_placeholder(match, parameter_values), template_text)
    return rendered.strip()


def serialize_template_instance(instance: TemplateInstance) -> dict[str, Any]:
    return {
        "id": instance.id,
        "schemaVersion": instance.schema_version,
        "templateId": instance.template_id,
        "template": copy.deepcopy(instance.template),
        "conversationId": instance.conversation_id,
        "chatId": instance.chat_id,
        "status": instance.status,
        "captureStage": instance.capture_stage,
        "revision": instance.revision,
        "parameters": copy.deepcopy(instance.parameters),
        "parameterConfirmation": copy.deepcopy(instance.parameter_confirmation),
        "catalogs": copy.deepcopy(instance.catalogs),
        "warnings": copy.deepcopy(instance.warnings),
        "createdAt": _isoformat(instance.created_at),
        "updatedAt": _isoformat(instance.updated_at),
    }


def collect_template_parameters(template: dict[str, Any]) -> list[dict[str, Any]]:
    parameters: list[dict[str, Any]] = []
    parameters.extend(copy.deepcopy(list(template.get("parameters") or [])))
    for catalog in list(template.get("catalogs") or []):
        parameters.extend(_collect_catalog_template_parameters(catalog))
    return parameters


def _collect_catalog_template_parameters(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    parameters: list[dict[str, Any]] = []
    parameters.extend(copy.deepcopy(list(catalog.get("parameters") or [])))
    for section in list(catalog.get("sections") or []):
        parameters.extend(copy.deepcopy(list(section.get("parameters") or [])))
    for sub_catalog in list(catalog.get("subCatalogs") or []):
        parameters.extend(_collect_catalog_template_parameters(sub_catalog))
    return parameters


def collect_instance_parameters(
    *,
    parameters: list[dict[str, Any]] | None,
    catalogs: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    collected = copy.deepcopy(list(parameters or []))
    for catalog in list(catalogs or []):
        collected.extend(_collect_catalog_instance_parameters(catalog))
    return collected


def _collect_catalog_instance_parameters(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    collected = copy.deepcopy(list(catalog.get("parameters") or []))
    for section in list(catalog.get("sections") or []):
        collected.extend(copy.deepcopy(list(section.get("parameters") or [])))
    for sub_catalog in list(catalog.get("subCatalogs") or []):
        collected.extend(_collect_catalog_instance_parameters(sub_catalog))
    return collected


def _render_item_placeholder(match: re.Match[str], item_lookup: dict[str, dict[str, Any]]) -> str:
    item_id = match.group(1)
    channel = match.group(2) or "label"
    item = item_lookup.get(item_id)
    if not item:
        return ""
    values = _normalize_parameter_value_list(item.get("values") or [])
    return _render_value_channel(values, channel)


def _render_parameter_placeholder(match: re.Match[str], parameter_values: dict[str, list[dict[str, Any]]]) -> str:
    parameter_id = match.group(1)
    channel = match.group(2) or "label"
    values = _normalize_parameter_value_list(parameter_values.get(parameter_id) or [])
    return _render_value_channel(values, channel)


def _render_value_channel(values: list[dict[str, Any]], channel: str) -> str:
    rendered = [str(value.get(channel) or value.get("label") or "") for value in values]
    return "、".join([text for text in rendered if text])


def build_resolved_query(values: list[dict[str, Any]]) -> str:
    queries = [str(value.get("query") or "").strip() for value in values if str(value.get("query") or "").strip()]
    if not queries:
        return ""
    if len(queries) == 1:
        return queries[0]
    parsed = [_parse_sql_equals(query) for query in queries]
    if parsed and all(item is not None for item in parsed):
        left = parsed[0][0]
        if all(item[0] == left for item in parsed):
            right_values = ", ".join(item[1] for item in parsed)
            return f"{left} IN ({right_values})"
    return " OR ".join(f"({query})" for query in queries)


def _default_multi_value_query_mode(values: list[dict[str, Any]]) -> str:
    queries = [str(value.get("query") or "").strip() for value in values if str(value.get("query") or "").strip()]
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


def _normalize_parameter_value_list(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    normalized: list[dict[str, Any]] = []
    for value in values:
        normalized_value = _normalize_parameter_value(value)
        if normalized_value:
            normalized.append(normalized_value)
    return normalized


def _normalize_parameter_value(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    if not {"label", "value", "query"}.issubset(value.keys()):
        return None
    return {
        "label": value.get("label"),
        "value": value.get("value"),
        "query": value.get("query"),
    }


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")
