from __future__ import annotations

import copy
import uuid
from typing import Any, Dict, List, Tuple

from ...template_catalog.domain.models import ReportTemplate
from ..domain.services import OutlineExpansionService, is_v2_template
from .rendering import build_outline_tree_v2


def build_pending_outline_review(
    template: ReportTemplate,
    input_params: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    if is_v2_template(template):
        return build_outline_tree_v2({"name": template.name, "sections": template.sections or []}, input_params or {})

    expansion = OutlineExpansionService().expand(template.outline or [], input_params or {})
    return _treeify_legacy_outline(expansion.nodes), expansion.warnings


def build_frontend_outline(outline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_sanitize_outline_node(item, include_internal=False) for item in outline]


def build_persisted_outline_snapshot(outline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_sanitize_outline_node(item, include_internal=True) for item in outline]


def resolve_outline_execution_baseline(outline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_resolve_outline_node(item) for item in outline if isinstance(item, dict)]


def flatten_review_outline(outline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flattened: List[Dict[str, Any]] = []
    for node in outline or []:
        if not isinstance(node, dict):
            continue
        payload = {
            "title": str(node.get("title") or "").strip(),
            "description": str(node.get("description") or "").strip(),
            "level": max(1, int(node.get("level") or 1)),
        }
        if isinstance(node.get("dynamic_meta"), dict):
            payload["dynamic_meta"] = copy.deepcopy(node.get("dynamic_meta"))
        flattened.append(payload)
        flattened.extend(flatten_review_outline(node.get("children") or []))
    return flattened


def merge_outline_override(
    current_outline: List[Dict[str, Any]],
    override_outline: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    current_lookup = {str(node.get("node_id") or ""): node for node in _walk_outline(current_outline)}
    return _merge_outline_list(override_outline, current_lookup, level=1)


def _merge_outline_list(
    override_nodes: List[Dict[str, Any]],
    current_lookup: Dict[str, Dict[str, Any]],
    *,
    level: int,
) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    for raw in override_nodes or []:
        if not isinstance(raw, dict):
            continue
        node_id = str(raw.get("node_id") or "").strip() or f"node-{uuid.uuid4().hex[:8]}"
        current = copy.deepcopy(current_lookup.get(node_id) or {})
        children = _merge_outline_list(raw.get("children") or [], current_lookup, level=level + 1)

        if not current:
            current = {
                "node_id": node_id,
                "title": str(raw.get("title") or "").strip(),
                "description": str(raw.get("description") or "").strip(),
                "level": level,
                "children": children,
                "section_kind": "freeform_leaf",
                "source_kind": "manual",
            }
        else:
            current["node_id"] = node_id
            current["title"] = str(raw.get("title") or "").strip()
            current["description"] = str(raw.get("description") or "").strip()
            current["level"] = level
            current["children"] = children
        outline_mode = str(raw.get("outline_mode") or "").strip()
        if outline_mode == "freeform":
            current.pop("requirement_instance", None)
            current.pop("execution_bindings", None)
            current.pop("content", None)
            current.pop("resolved_content", None)
            current["source_kind"] = "manual"
            current["section_kind"] = "group" if children else "freeform_leaf"
        else:
            merged_requirement_instance = _merge_requirement_instance(raw.get("requirement_instance"), current.get("requirement_instance"))
            if merged_requirement_instance:
                current["requirement_instance"] = merged_requirement_instance
        current.pop("display_text", None)
        current.pop("ai_generated", None)
        current.pop("node_kind", None)
        current.pop("outline_mode", None)

        if children:
            current["section_kind"] = "group"
            current.pop("content", None)
        elif not current.get("content"):
            current["section_kind"] = "freeform_leaf"
            current.setdefault("source_kind", "manual")

        merged.append(current)
    return merged


def _treeify_legacy_outline(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    roots: List[Dict[str, Any]] = []
    stack: List[Dict[str, Any]] = []
    for index, item in enumerate(items or []):
        if not isinstance(item, dict):
            continue
        level = max(1, int(item.get("level") or 1))
        node = {
            "node_id": f"legacy-{index}",
            "title": str(item.get("title") or "").strip(),
            "description": str(item.get("description") or "").strip(),
            "level": level,
            "children": [],
            "section_kind": "freeform_leaf",
            "node_kind": "freeform_leaf",
            "source_kind": "legacy",
            "ai_generated": True,
        }
        node["display_text"] = _build_display_text(node["title"], node["description"])
        if isinstance(item.get("dynamic_meta"), dict):
            node["dynamic_meta"] = copy.deepcopy(item.get("dynamic_meta"))
        while stack and int(stack[-1]["level"]) >= level:
            stack.pop()
        if stack:
            stack[-1]["section_kind"] = "group"
            stack[-1]["node_kind"] = "group"
            stack[-1]["ai_generated"] = False
            stack[-1]["display_text"] = _build_display_text(stack[-1].get("title"), stack[-1].get("description"))
            stack[-1].setdefault("children", []).append(node)
        else:
            roots.append(node)
        stack.append(node)
    return roots


def _sanitize_outline_node(node: Dict[str, Any], *, include_internal: bool) -> Dict[str, Any]:
    title = str(node.get("title") or "")
    description = str(node.get("description") or "")
    node_kind = str(node.get("node_kind") or node.get("section_kind") or ("group" if node.get("children") else "freeform_leaf"))
    requirement_instance = node.get("requirement_instance") if isinstance(node.get("requirement_instance"), dict) else {}
    rendered_outline = str(requirement_instance.get("rendered_requirement") or "").strip()
    payload = {
        "node_id": str(node.get("node_id") or ""),
        "title": title,
        "description": description,
        "level": max(1, int(node.get("level") or 1)),
        "display_text": str(node.get("display_text") or rendered_outline or _build_display_text(title, description)),
        "ai_generated": bool(node.get("ai_generated")),
        "node_kind": node_kind,
        "children": [
            _sanitize_outline_node(child, include_internal=include_internal)
            for child in node.get("children") or []
            if isinstance(child, dict)
        ],
    }
    if isinstance(node.get("dynamic_meta"), dict):
        payload["dynamic_meta"] = copy.deepcopy(node.get("dynamic_meta"))
    if requirement_instance:
        payload["requirement_instance"] = copy.deepcopy(requirement_instance)
    if isinstance(node.get("execution_bindings"), list):
        payload["execution_bindings"] = copy.deepcopy(node.get("execution_bindings"))
    if include_internal:
        if isinstance(node.get("content"), dict):
            payload["content"] = copy.deepcopy(node.get("content"))
        if isinstance(node.get("resolved_content"), dict):
            payload["resolved_content"] = copy.deepcopy(node.get("resolved_content"))
        section_kind = str(node.get("section_kind") or "").strip()
        if section_kind:
            payload["section_kind"] = section_kind
        source_kind = str(node.get("source_kind") or "").strip()
        if source_kind:
            payload["source_kind"] = source_kind
    return payload


def _resolve_outline_node(node: Dict[str, Any]) -> Dict[str, Any]:
    payload = copy.deepcopy(node)
    outline_ctx = _outline_context_from_node(node)
    if isinstance(payload.get("content"), dict):
        payload["resolved_content"] = _resolve_outline_placeholders(payload["content"], outline_ctx)
    payload["children"] = [
        _resolve_outline_node(child)
        for child in payload.get("children") or []
        if isinstance(child, dict)
    ]
    return payload


def _outline_context_from_node(node: Dict[str, Any]) -> Dict[str, Any]:
    requirement_instance = node.get("requirement_instance") if isinstance(node.get("requirement_instance"), dict) else {}
    context: Dict[str, Any] = {}
    for item in requirement_instance.get("items") or requirement_instance.get("slots") or []:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip()
        if not item_id:
            continue
        context[item_id] = item.get("value")
    return context


def _merge_requirement_instance(override: Any, current: Any) -> Dict[str, Any] | None:
    if not isinstance(override, dict):
        return copy.deepcopy(current) if isinstance(current, dict) else None

    current_instance = current if isinstance(current, dict) else {}
    current_items = {
        str(item.get("id") or "").strip(): copy.deepcopy(item)
        for item in current_instance.get("items") or current_instance.get("slots") or []
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }

    override_items = override.get("items")
    if not isinstance(override_items, list):
        override_items = override.get("slots") or []

    merged_items: List[Dict[str, Any]] = []
    for raw_item in override_items or []:
        if not isinstance(raw_item, dict):
            continue
        item_id = str(raw_item.get("id") or "").strip()
        if not item_id:
            continue
        merged_item = current_items.get(item_id, {})
        merged_item.update(copy.deepcopy(raw_item))
        merged_item["id"] = item_id
        merged_item["value"] = str(merged_item.get("value") or "")
        merged_items.append(merged_item)

    merged_item_lookup = {
        str(item.get("id") or "").strip(): item
        for item in merged_items
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }

    merged_segments: List[Dict[str, Any]] = []
    segments_input = override.get("segments") if isinstance(override.get("segments"), list) else current_instance.get("segments")
    for raw_segment in segments_input or []:
        if not isinstance(raw_segment, dict):
            continue
        kind = str(raw_segment.get("kind") or "").strip()
        if kind == "text":
            merged_segments.append({"kind": "text", "text": str(raw_segment.get("text") or "")})
            continue
        if kind != "item":
            continue
        item_id = str(raw_segment.get("item_id") or raw_segment.get("slot_id") or "").strip()
        if not item_id:
            continue
        item = merged_item_lookup.get(item_id, {})
        merged_segments.append(
            {
                "kind": "item",
                "item_id": item_id,
                "item_type": str(raw_segment.get("item_type") or raw_segment.get("slot_type") or item.get("type") or ""),
                "value": str(item.get("value") or raw_segment.get("value") or ""),
            }
        )

    rendered_requirement = "".join(
        str(segment.get("text") if segment.get("kind") == "text" else segment.get("value") or "")
        for segment in merged_segments
    ).strip()
    requirement = str(override.get("requirement") or override.get("requirement_template") or current_instance.get("requirement") or current_instance.get("requirement_template") or "")
    if not rendered_requirement:
        rendered_requirement = str(override.get("rendered_requirement") or current_instance.get("rendered_requirement") or "").strip()

    return {
        "requirement": requirement,
        "rendered_requirement": rendered_requirement,
        "segments": merged_segments,
        "items": merged_items,
    }


def _resolve_outline_placeholders(value: Any, outline_ctx: Dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _resolve_outline_placeholders(item, outline_ctx) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_outline_placeholders(item, outline_ctx) for item in value]
    if isinstance(value, str):
        return _replace_outline_tokens(value, outline_ctx)
    return copy.deepcopy(value)


def _replace_outline_tokens(text: str, outline_ctx: Dict[str, Any]) -> str:
    def replace(match):
        key = str(match.group(1) or "").strip()
        return str(outline_ctx.get(key) or "")

    import re

    return re.sub(r"\{@([a-zA-Z0-9_]+)\}", replace, text or "")


def _walk_outline(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    walked: List[Dict[str, Any]] = []
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        walked.append(node)
        walked.extend(_walk_outline(node.get("children") or []))
    return walked


def _build_display_text(title: Any, description: Any) -> str:
    title_text = str(title or "").strip()
    description_text = str(description or "").strip()
    if title_text and description_text:
        return f"{title_text}：{description_text}"
    return title_text or description_text
