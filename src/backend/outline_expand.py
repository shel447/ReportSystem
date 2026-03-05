from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Dict, List, Tuple

PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}")


def expand_outline(outline: List[Any], input_params: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Expand template outline with param bindings and repeat rules.

    The expander is resilient by design: invalid repeat definitions or missing
    parameters produce warnings and do not abort generation.
    """
    warnings: List[str] = []
    expanded: List[Dict[str, Any]] = []

    for idx, raw_item in enumerate(outline or []):
        if not isinstance(raw_item, dict):
            warnings.append(f"outline[{idx}] is not an object, skipped")
            continue

        repeat = raw_item.get("repeat") or {}
        enabled = bool(repeat.get("enabled")) if isinstance(repeat, dict) else False

        if enabled:
            source_param = str(repeat.get("source_param") or "").strip()
            if not source_param:
                warnings.append(f"outline[{idx}] repeat is enabled but source_param is empty, skipped")
                continue

            raw_value = input_params.get(source_param)
            items = _normalize_list(raw_value)
            if items is None:
                warnings.append(
                    f"outline[{idx}] repeat source '{source_param}' is missing or not a list/string, skipped"
                )
                continue
            if not items:
                warnings.append(f"outline[{idx}] repeat source '{source_param}' is empty, skipped")
                continue

            item_alias = str(repeat.get("item_alias") or "item")
            index_alias = str(repeat.get("index_alias") or "index")

            for item_index, entry in enumerate(items):
                context = _build_context(
                    input_params=input_params,
                    bindings=raw_item.get("bindings") or {},
                    repeat_item=entry,
                    item_index=item_index,
                    item_alias=item_alias,
                    index_alias=index_alias,
                )
                item_warnings: List[str] = []
                rendered = _render_outline_item(raw_item, context, item_warnings)
                for w in item_warnings:
                    warnings.append(f"outline[{idx}] item[{item_index}] {w}")

                rendered["dynamic_meta"] = {
                    "source_param": source_param,
                    "item_alias": item_alias,
                    "index_alias": index_alias,
                    "item": entry,
                    "index": item_index,
                }
                expanded.append(rendered)
            continue

        context = _build_context(
            input_params=input_params,
            bindings=raw_item.get("bindings") or {},
            repeat_item=None,
            item_index=None,
            item_alias="item",
            index_alias="index",
        )
        item_warnings = []
        rendered = _render_outline_item(raw_item, context, item_warnings)
        for w in item_warnings:
            warnings.append(f"outline[{idx}] {w}")
        expanded.append(rendered)

    return expanded, warnings


def _normalize_list(value: Any) -> List[Any] | None:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return None


def _build_context(
    input_params: Dict[str, Any],
    bindings: Dict[str, Any],
    repeat_item: Any,
    item_index: int | None,
    item_alias: str,
    index_alias: str,
) -> Dict[str, Any]:
    # Priority baseline: input_params
    context: Dict[str, Any] = dict(input_params or {})

    # Then mapped aliases from bindings.extra
    extra = bindings.get("extra") if isinstance(bindings, dict) else None
    if isinstance(extra, dict):
        for alias, path in extra.items():
            if isinstance(path, str) and path.strip():
                value = _resolve_path(context, path)
                if value is not None:
                    context[alias] = value

    # Then repeat scope (highest priority)
    if repeat_item is not None:
        context[item_alias] = repeat_item
        context[index_alias] = item_index
        if item_alias != "item":
            context["item"] = repeat_item
        if index_alias != "index":
            context["index"] = item_index

    # Finally explicit title/description binding entries.
    if isinstance(bindings, dict):
        if isinstance(bindings.get("title"), str) and bindings["title"].strip():
            bound_title = _resolve_path(context, bindings["title"])
            if bound_title is not None:
                context["title"] = bound_title
        if isinstance(bindings.get("description"), str) and bindings["description"].strip():
            bound_desc = _resolve_path(context, bindings["description"])
            if bound_desc is not None:
                context["description"] = bound_desc

    return context


def _render_outline_item(item: Dict[str, Any], context: Dict[str, Any], warnings: List[str]) -> Dict[str, Any]:
    rendered = deepcopy(item)

    title_template = item.get("title_template")
    desc_template = item.get("description_template")

    if isinstance(title_template, str) and title_template.strip():
        rendered["title"] = _render_template(title_template, context, warnings)
    else:
        rendered["title"] = item.get("title", "")

    if isinstance(desc_template, str) and desc_template.strip():
        rendered["description"] = _render_template(desc_template, context, warnings)
    else:
        rendered["description"] = item.get("description", "")

    return rendered


def _render_template(template: str, context: Dict[str, Any], warnings: List[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        path = match.group(1)
        value = _resolve_path(context, path)
        if value is None:
            warnings.append(f"placeholder '{{{{{path}}}}}' unresolved")
            return ""
        return str(value)

    return PLACEHOLDER_PATTERN.sub(replace, template)


def _resolve_path(data: Any, path: str) -> Any:
    current = data
    for token in path.split("."):
        if isinstance(current, dict):
            if token not in current:
                return None
            current = current[token]
            continue

        if isinstance(current, list):
            if not token.isdigit():
                return None
            index = int(token)
            if index < 0 or index >= len(current):
                return None
            current = current[index]
            continue

        return None
    return current
