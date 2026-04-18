from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from typing import Any

from .models import TemplateInstance

PLACEHOLDER_PATTERN = re.compile(r"\{@([A-Za-z0-9_\-]+)(?:\.(display|value|query))?\}")


def merge_parameter_values(
    *,
    parameter_definitions: list[dict[str, Any]],
    current_values: dict[str, list[dict[str, Any]]] | None,
    incoming_values: dict[str, list[dict[str, Any]]] | None,
) -> dict[str, list[dict[str, Any]]]:
    merged = copy.deepcopy(current_values or {})
    incoming = incoming_values or {}
    for definition in parameter_definitions:
        param_id = str(definition.get("id") or "").strip()
        if not param_id:
            continue
        if param_id in incoming and incoming[param_id] is not None:
            merged[param_id] = _normalize_trio_list(incoming[param_id])
            continue
        if param_id not in merged:
            default_value = definition.get("defaultValue")
            if isinstance(default_value, list):
                merged[param_id] = _normalize_trio_list(default_value)
    return merged


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
    existing_delta_views: list[dict[str, Any]] | None = None,
    warnings: list[dict[str, Any]] | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> TemplateInstance:
    parameter_definitions = list(template.get("parameters") or [])
    effective_values = merge_parameter_values(
        parameter_definitions=parameter_definitions,
        current_values=parameter_values,
        incoming_values={},
    )
    catalogs = build_catalog_instances(template=template, parameter_values=effective_values)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return TemplateInstance(
        id=instance_id,
        schema_version="template-instance.v2",
        template_id=str(template.get("id") or ""),
        conversation_id=conversation_id,
        chat_id=chat_id,
        status=status,
        capture_stage=capture_stage,
        revision=revision,
        parameter_values=effective_values,
        catalogs=catalogs,
        delta_views=list(existing_delta_views or []),
        template_skeleton_status={"internal": "reusable", "ui": "not_broken"},
        warnings=list(warnings or []),
        created_at=created_at or now,
        updated_at=updated_at or now,
    )


def build_catalog_instances(*, template: dict[str, Any], parameter_values: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    catalogs: list[dict[str, Any]] = []
    for catalog in list(template.get("catalogs") or []):
        sections: list[dict[str, Any]] = []
        for section in list(catalog.get("sections") or []):
            sections.extend(expand_section_instances(section=section, parameter_values=parameter_values))
        catalogs.append(
            {
                "id": catalog.get("id"),
                "name": catalog.get("name"),
                "description": catalog.get("description"),
                "order": catalog.get("order"),
                "sections": sections,
            }
        )
    return catalogs


def expand_section_instances(*, section: dict[str, Any], parameter_values: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    foreach = section.get("foreach") if isinstance(section.get("foreach"), dict) else None
    if not foreach:
        return [build_section_instance(section=section, parameter_values=parameter_values)]

    parameter_id = str(foreach.get("parameterId") or "").strip()
    values = list(parameter_values.get(parameter_id) or [])
    if not parameter_id or not values:
        return [build_section_instance(section=section, parameter_values=parameter_values)]

    expanded: list[dict[str, Any]] = []
    for index, value in enumerate(values, start=1):
        scoped_values = copy.deepcopy(parameter_values)
        scoped_values[parameter_id] = [value]
        built = build_section_instance(section=section, parameter_values=scoped_values)
        built["id"] = f"{built['id']}__{index}"
        display = str(value.get("display") or value.get("value") or index)
        built["title"] = f"{section.get('title')} - {display}"
        expanded.append(built)
    return expanded


def build_section_instance(*, section: dict[str, Any], parameter_values: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    outline = section.get("outline") if isinstance(section.get("outline"), dict) else {}
    item_instances = []
    for item in list(outline.get("items") or []):
        item_instances.append(build_requirement_item_instance(item=item, parameter_values=parameter_values))
    item_lookup = {item["id"]: item for item in item_instances}
    requirement_text = render_requirement_text(str(outline.get("requirement") or ""), item_lookup)
    return {
        "id": section.get("id"),
        "title": section.get("title"),
        "description": section.get("description"),
        "order": section.get("order"),
        "requirementInstance": {
            "text": requirement_text,
            "items": item_instances,
        },
        "executionBindings": build_execution_bindings(section=section, item_instances=item_instances),
        "skeletonStatus": "reusable",
        "userEdited": False,
    }


def build_requirement_item_instance(*, item: dict[str, Any], parameter_values: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    source_parameter_id = str(item.get("sourceParameterId") or "").strip()
    resolved_values = []
    binding_source = "system_fill"
    if source_parameter_id:
        resolved_values = _normalize_trio_list(parameter_values.get(source_parameter_id) or item.get("defaultValue") or [])
        binding_source = "parameter"
    else:
        resolved_values = _normalize_trio_list(item.get("defaultValue") or [])
    return {
        "id": item.get("id"),
        "label": item.get("label"),
        "kind": item.get("kind"),
        "resolvedValues": resolved_values,
        "bindingSource": binding_source,
        "sourceParameterId": source_parameter_id or None,
    }


def build_execution_bindings(*, section: dict[str, Any], item_instances: list[dict[str, Any]]) -> list[dict[str, Any]]:
    datasets = ((section.get("content") or {}).get("datasets") or []) if isinstance(section.get("content"), dict) else []
    bindings: list[dict[str, Any]] = []
    for dataset in datasets:
        dataset_id = str(dataset.get("id") or "")
        for item in item_instances:
            resolved_values = list(item.get("resolvedValues") or [])
            bindings.append(
                {
                    "id": f"binding_{dataset_id}_{item.get('id')}",
                    "bindingType": "dataset_parameter",
                    "sourceType": dataset.get("sourceType") or "sql",
                    "targetRef": f"{dataset_id}.{item.get('id')}",
                    "multiValueQueryMode": "in" if len(resolved_values) > 1 else "single",
                    "resolvedQuery": build_resolved_query(resolved_values),
                }
            )
    return bindings


def render_requirement_text(template_text: str, item_lookup: dict[str, dict[str, Any]]) -> str:
    def replace(match: re.Match[str]) -> str:
        item_id = match.group(1)
        channel = match.group(2) or "display"
        item = item_lookup.get(item_id)
        if not item:
            return ""
        values = list(item.get("resolvedValues") or [])
        rendered = [str(value.get(channel) or value.get("display") or "") for value in values]
        return "、".join([text for text in rendered if text])

    return PLACEHOLDER_PATTERN.sub(replace, template_text).strip()


def build_resolved_query(values: list[dict[str, Any]]) -> str:
    if not values:
        return ""
    queries = [value.get("query") for value in values if value.get("query") is not None]
    if not queries:
        return ""
    if len(queries) == 1:
        return str(queries[0])
    quoted = ", ".join(f"'{item}'" if isinstance(item, str) else str(item) for item in queries)
    return f"IN ({quoted})"


def serialize_template_instance(instance: TemplateInstance) -> dict[str, Any]:
    return {
        "id": instance.id,
        "schemaVersion": instance.schema_version,
        "templateId": instance.template_id,
        "conversationId": instance.conversation_id,
        "chatId": instance.chat_id,
        "status": instance.status,
        "captureStage": instance.capture_stage,
        "revision": instance.revision,
        "parameterValues": copy.deepcopy(instance.parameter_values),
        "catalogs": copy.deepcopy(instance.catalogs),
        "deltaViews": copy.deepcopy(instance.delta_views),
        "templateSkeletonStatus": copy.deepcopy(instance.template_skeleton_status),
        "warnings": copy.deepcopy(instance.warnings),
        "createdAt": _isoformat(instance.created_at),
        "updatedAt": _isoformat(instance.updated_at),
    }


def _normalize_trio_list(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    normalized: list[dict[str, Any]] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        if {"display", "value", "query"}.issubset(value.keys()):
            normalized.append(
                {
                    "display": value.get("display"),
                    "value": value.get("value"),
                    "query": value.get("query"),
                }
            )
    return normalized


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")
