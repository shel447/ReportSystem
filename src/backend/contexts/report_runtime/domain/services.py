from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True, slots=True)
class ExpandedOutline:
    nodes: list[dict[str, Any]]
    warnings: list[str]


_PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}")


def is_v2_template(template: Any) -> bool:
    sections = getattr(template, "sections", None)
    return isinstance(sections, list)


class OutlineExpansionService:
    def expand(self, outline: list[Any], input_params: dict[str, Any]) -> ExpandedOutline:
        warnings: list[str] = []
        expanded: list[dict[str, Any]] = []

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
                items = self._normalize_list(raw_value)
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
                    context = self._build_context(
                        input_params=input_params,
                        bindings=raw_item.get("bindings") or {},
                        repeat_item=entry,
                        item_index=item_index,
                        item_alias=item_alias,
                        index_alias=index_alias,
                    )
                    item_warnings: list[str] = []
                    rendered = self._render_outline_item(raw_item, context, item_warnings)
                    for warning in item_warnings:
                        warnings.append(f"outline[{idx}] item[{item_index}] {warning}")

                    rendered["dynamic_meta"] = {
                        "source_param": source_param,
                        "item_alias": item_alias,
                        "index_alias": index_alias,
                        "item": entry,
                        "index": item_index,
                    }
                    expanded.append(rendered)
                continue

            context = self._build_context(
                input_params=input_params,
                bindings=raw_item.get("bindings") or {},
                repeat_item=None,
                item_index=None,
                item_alias="item",
                index_alias="index",
            )
            item_warnings: list[str] = []
            rendered = self._render_outline_item(raw_item, context, item_warnings)
            for warning in item_warnings:
                warnings.append(f"outline[{idx}] {warning}")
            expanded.append(rendered)

        return ExpandedOutline(nodes=expanded, warnings=warnings)

    @staticmethod
    def _normalize_list(value: Any) -> list[Any] | None:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return None

    def _build_context(
        self,
        *,
        input_params: dict[str, Any],
        bindings: dict[str, Any],
        repeat_item: Any,
        item_index: int | None,
        item_alias: str,
        index_alias: str,
    ) -> dict[str, Any]:
        context: dict[str, Any] = dict(input_params or {})

        extra = bindings.get("extra") if isinstance(bindings, dict) else None
        if isinstance(extra, dict):
            for alias, path in extra.items():
                if isinstance(path, str) and path.strip():
                    value = self._resolve_path(context, path)
                    if value is not None:
                        context[alias] = value

        if repeat_item is not None:
            context[item_alias] = repeat_item
            context[index_alias] = item_index
            if item_alias != "item":
                context["item"] = repeat_item
            if index_alias != "index":
                context["index"] = item_index

        if isinstance(bindings, dict):
            title_binding = bindings.get("title")
            if isinstance(title_binding, str) and title_binding.strip():
                value = self._resolve_path(context, title_binding)
                if value is not None:
                    context["title"] = value
            desc_binding = bindings.get("description")
            if isinstance(desc_binding, str) and desc_binding.strip():
                value = self._resolve_path(context, desc_binding)
                if value is not None:
                    context["description"] = value

        return context

    def _render_outline_item(
        self,
        item: dict[str, Any],
        context: dict[str, Any],
        warnings: list[str],
    ) -> dict[str, Any]:
        rendered = deepcopy(item)

        title_template = item.get("title_template")
        desc_template = item.get("description_template")

        if isinstance(title_template, str) and title_template.strip():
            rendered["title"] = self._render_template(title_template, context, warnings)
        else:
            rendered["title"] = item.get("title", "")

        if isinstance(desc_template, str) and desc_template.strip():
            rendered["description"] = self._render_template(desc_template, context, warnings)
        else:
            rendered["description"] = item.get("description", "")

        return rendered

    def _render_template(self, template: str, context: dict[str, Any], warnings: list[str]) -> str:
        def replace(match: re.Match[str]) -> str:
            path = match.group(1)
            value = self._resolve_path(context, path)
            if value is None:
                warnings.append(f"placeholder '{{{{{path}}}}}' unresolved")
                return ""
            return str(value)

        return _PLACEHOLDER_PATTERN.sub(replace, template)

    def _resolve_path(self, data: Any, path: str) -> Any:
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
                idx = int(token)
                if idx < 0 or idx >= len(current):
                    return None
                current = current[idx]
                continue
            return None
        return current
