from __future__ import annotations

import copy
import uuid
from typing import Any, Dict, List, Tuple

from .domain.reporting.entities import ReportTemplateEntity
from .domain.reporting.services import OutlineExpansionService
from .template_v2_renderer import build_outline_tree_v2


def build_pending_outline_review(
    template: ReportTemplateEntity,
    input_params: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    if _is_v2_template(template):
        return build_outline_tree_v2({"name": template.name, "sections": template.sections or []}, input_params or {})

    expansion = OutlineExpansionService().expand(template.outline or [], input_params or {})
    return _treeify_legacy_outline(expansion.nodes), expansion.warnings


def build_frontend_outline(outline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_sanitize_outline_node(item) for item in outline]


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
            "source_kind": "legacy",
        }
        if isinstance(item.get("dynamic_meta"), dict):
            node["dynamic_meta"] = copy.deepcopy(item.get("dynamic_meta"))
        while stack and int(stack[-1]["level"]) >= level:
            stack.pop()
        if stack:
            stack[-1].setdefault("children", []).append(node)
        else:
            roots.append(node)
        stack.append(node)
    return roots


def _sanitize_outline_node(node: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "node_id": str(node.get("node_id") or ""),
        "title": str(node.get("title") or ""),
        "description": str(node.get("description") or ""),
        "level": max(1, int(node.get("level") or 1)),
        "children": [_sanitize_outline_node(child) for child in node.get("children") or [] if isinstance(child, dict)],
    }
    if isinstance(node.get("dynamic_meta"), dict):
        payload["dynamic_meta"] = copy.deepcopy(node.get("dynamic_meta"))
    return payload


def _walk_outline(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    walked: List[Dict[str, Any]] = []
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        walked.append(node)
        walked.extend(_walk_outline(node.get("children") or []))
    return walked


def _is_v2_template(template: ReportTemplateEntity) -> bool:
    return bool(getattr(template, "sections", None))
