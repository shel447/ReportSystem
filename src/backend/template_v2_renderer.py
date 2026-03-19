from __future__ import annotations

import copy
import json
import os
import re
import sqlite3
from typing import Any, Callable, Dict, List, Optional, Tuple


DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "telecom_demo.db")


def generate_report_sections_v2(
    template: Dict[str, Any],
    input_params: Dict[str, Any],
    *,
    db_path: Optional[str] = None,
    nl2sql_runner: Optional[Callable[..., Dict[str, Any]]] = None,
    ai_synthesis_runner: Optional[Callable[..., str]] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    outline_tree, warnings = build_outline_tree_v2(template, input_params)
    rendered, render_warnings = generate_report_sections_from_outline_tree_v2(
        template,
        outline_tree,
        input_params,
        db_path=db_path,
        nl2sql_runner=nl2sql_runner,
        ai_synthesis_runner=ai_synthesis_runner,
    )
    warnings.extend(render_warnings)
    return rendered, warnings


def build_outline_tree_v2(
    template: Dict[str, Any],
    input_params: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    warnings: List[str] = []
    sections = _as_list(template.get("sections"))
    outline_tree: List[Dict[str, Any]] = []
    for index, item in enumerate(sections):
        outline_tree.extend(
            _build_outline_node(
                item,
                input_params,
                warnings,
                locals_ctx={},
                path_prefix=f"sec-{index}",
                level=1,
            )
        )
    return outline_tree, warnings


def generate_report_sections_from_outline_tree_v2(
    template: Dict[str, Any],
    outline_tree: List[Dict[str, Any]],
    input_params: Dict[str, Any],
    *,
    db_path: Optional[str] = None,
    nl2sql_runner: Optional[Callable[..., Dict[str, Any]]] = None,
    ai_synthesis_runner: Optional[Callable[..., str]] = None,
    freeform_runner: Optional[Callable[..., Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    warnings: List[str] = []
    rendered: List[Dict[str, Any]] = []
    for node in outline_tree or []:
        rendered.extend(
            _render_outline_tree_node(
                node,
                input_params,
                warnings,
                db_path=db_path or DEFAULT_DB_PATH,
                nl2sql_runner=nl2sql_runner,
                ai_synthesis_runner=ai_synthesis_runner,
                freeform_runner=freeform_runner,
            )
        )
    return rendered, warnings


def _render_section(
    section: Dict[str, Any],
    params: Dict[str, Any],
    warnings: List[str],
    locals_ctx: Dict[str, Any],
    *,
    db_path: str,
    nl2sql_runner: Optional[Callable[..., Dict[str, Any]]],
    ai_synthesis_runner: Optional[Callable[..., str]],
) -> List[Dict[str, Any]]:
    if not isinstance(section, dict):
        return []

    foreach = section.get("foreach") if isinstance(section.get("foreach"), dict) else None
    if foreach:
        return _expand_foreach(
            section,
            params,
            warnings,
            locals_ctx,
            db_path=db_path,
            nl2sql_runner=nl2sql_runner,
            ai_synthesis_runner=ai_synthesis_runner,
        )

    title = _render_text(str(section.get("title") or ""), params, locals_ctx)
    description = _render_text(str(section.get("description") or ""), params, locals_ctx)
    level = max(1, min(6, int(section.get("level") or 1)))

    children = _as_list(section.get("subsections"))
    if children:
        rendered: List[Dict[str, Any]] = [
            {
                "title": title,
                "description": description,
                "content": "",
                "status": "generated",
                "data_status": "success",
                "debug": {},
                "level": level,
            }
        ]
        for child in children:
            rendered.extend(
                _render_section(
                    child,
                    params,
                    warnings,
                    locals_ctx,
                    db_path=db_path,
                    nl2sql_runner=nl2sql_runner,
                    ai_synthesis_runner=ai_synthesis_runner,
                )
            )
        return rendered

    content, debug, data_status = _render_content(
        section.get("content"),
        params,
        locals_ctx,
        warnings,
        db_path=db_path,
        nl2sql_runner=nl2sql_runner,
        ai_synthesis_runner=ai_synthesis_runner,
    )
    status = "generated" if data_status == "success" else "failed"

    return [
        {
            "title": title,
            "description": description,
            "content": content,
            "status": status,
            "data_status": data_status,
            "debug": debug,
            "level": level,
        }
    ]


def _expand_foreach(
    section: Dict[str, Any],
    params: Dict[str, Any],
    warnings: List[str],
    locals_ctx: Dict[str, Any],
    *,
    db_path: str,
    nl2sql_runner: Optional[Callable[..., Dict[str, Any]]],
    ai_synthesis_runner: Optional[Callable[..., str]],
) -> List[Dict[str, Any]]:
    foreach = section.get("foreach") or {}
    param_id = str(foreach.get("param") or "").strip()
    alias = str(foreach.get("as") or "item").strip()
    depth = int(locals_ctx.get("__foreach_depth__", 0) or 0)
    if depth >= 1:
        warnings.append("检测到嵌套 foreach，已忽略内层循环。")
        cloned = copy.deepcopy(section)
        cloned.pop("foreach", None)
        return _render_section(
            cloned,
            params,
            warnings,
            locals_ctx,
            db_path=db_path,
            nl2sql_runner=nl2sql_runner,
            ai_synthesis_runner=ai_synthesis_runner,
        )
    if not param_id:
        warnings.append("foreach 缺少 param 参数，已跳过。")
        return []
    values = params.get(param_id)
    if values is None:
        warnings.append(f"foreach 参数 {param_id} 缺失，已跳过。")
        return []
    if not isinstance(values, list):
        values = [values]
    rendered: List[Dict[str, Any]] = []
    for value in values:
        child_locals = dict(locals_ctx)
        child_locals[alias] = value
        child_locals["__foreach_depth__"] = depth + 1
        cloned = copy.deepcopy(section)
        cloned.pop("foreach", None)
        rendered.extend(
            _render_section(
                cloned,
                params,
                warnings,
                child_locals,
                db_path=db_path,
                nl2sql_runner=nl2sql_runner,
                ai_synthesis_runner=ai_synthesis_runner,
            )
        )
    return rendered


def _build_outline_node(
    section: Dict[str, Any],
    params: Dict[str, Any],
    warnings: List[str],
    locals_ctx: Dict[str, Any],
    *,
    path_prefix: str,
    level: int,
) -> List[Dict[str, Any]]:
    if not isinstance(section, dict):
        return []

    foreach = section.get("foreach") if isinstance(section.get("foreach"), dict) else None
    if foreach:
        return _expand_outline_foreach(
            section,
            params,
            warnings,
            locals_ctx,
            path_prefix=path_prefix,
            level=level,
        )

    title = _render_text(str(section.get("title") or ""), params, locals_ctx)
    description = _render_text(str(section.get("description") or ""), params, locals_ctx)
    node_level = max(1, min(6, int(section.get("level") or level)))
    node = {
        "node_id": f"node-{path_prefix}",
        "title": title,
        "description": description,
        "level": node_level,
        "children": [],
        "source_kind": "v2",
    }
    dynamic_meta = _dynamic_meta_from_locals(locals_ctx)
    if dynamic_meta:
        node["dynamic_meta"] = dynamic_meta

    children = _as_list(section.get("subsections"))
    if children:
        rendered_children: List[Dict[str, Any]] = []
        for index, child in enumerate(children):
            rendered_children.extend(
                _build_outline_node(
                    child,
                    params,
                    warnings,
                    locals_ctx,
                    path_prefix=f"{path_prefix}-{index}",
                    level=node_level + 1,
                )
            )
        node["section_kind"] = "group"
        node["node_kind"] = "group"
        node["display_text"] = _outline_display_text(title, description)
        node["ai_generated"] = False
        node["children"] = rendered_children
        return [node]

    content = section.get("content")
    if isinstance(content, dict):
        node["content"] = _normalize_content(content)
        node["section_kind"] = "structured_leaf"
        node["node_kind"] = "structured_leaf"
        node["ai_generated"] = _content_uses_ai(node["content"])
    else:
        node["section_kind"] = "freeform_leaf"
        node["node_kind"] = "freeform_leaf"
        node["ai_generated"] = True
    node["display_text"] = _outline_display_text(title, description)
    return [node]


def _expand_outline_foreach(
    section: Dict[str, Any],
    params: Dict[str, Any],
    warnings: List[str],
    locals_ctx: Dict[str, Any],
    *,
    path_prefix: str,
    level: int,
) -> List[Dict[str, Any]]:
    foreach = section.get("foreach") or {}
    param_id = str(foreach.get("param") or "").strip()
    alias = str(foreach.get("as") or "item").strip()
    depth = int(locals_ctx.get("__foreach_depth__", 0) or 0)
    if depth >= 1:
        warnings.append("检测到嵌套 foreach，已忽略内层循环。")
        cloned = copy.deepcopy(section)
        cloned.pop("foreach", None)
        return _build_outline_node(
            cloned,
            params,
            warnings,
            locals_ctx,
            path_prefix=path_prefix,
            level=level,
        )
    if not param_id:
        warnings.append("foreach 缺少 param 参数，已跳过。")
        return []
    values = params.get(param_id)
    if values is None:
        warnings.append(f"foreach 参数 {param_id} 缺失，已跳过。")
        return []
    if not isinstance(values, list):
        values = [values]
    rendered: List[Dict[str, Any]] = []
    for item_index, value in enumerate(values):
        child_locals = dict(locals_ctx)
        child_locals[alias] = value
        child_locals["__foreach_depth__"] = depth + 1
        child_locals["__dynamic_meta__"] = {
            "source_param": param_id,
            "item_alias": alias,
            "index_alias": "index",
            "item": value,
            "index": item_index,
        }
        cloned = copy.deepcopy(section)
        cloned.pop("foreach", None)
        rendered.extend(
            _build_outline_node(
                cloned,
                params,
                warnings,
                child_locals,
                path_prefix=f"{path_prefix}-r{item_index}",
                level=level,
            )
        )
    return rendered


def _render_outline_tree_node(
    node: Dict[str, Any],
    params: Dict[str, Any],
    warnings: List[str],
    *,
    db_path: str,
    nl2sql_runner: Optional[Callable[..., Dict[str, Any]]],
    ai_synthesis_runner: Optional[Callable[..., str]],
    freeform_runner: Optional[Callable[..., Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    title = str(node.get("title") or "")
    description = str(node.get("description") or "")
    level = max(1, min(6, int(node.get("level") or 1)))
    children = _as_list(node.get("children"))
    dynamic_meta = node.get("dynamic_meta") if isinstance(node.get("dynamic_meta"), dict) else None

    if children:
        rendered = [
            {
                "title": title,
                "description": description,
                "content": "",
                "status": "generated",
                "data_status": "success",
                "debug": {"outline_node": copy.deepcopy(node)},
                "level": level,
                **({"dynamic_meta": dynamic_meta} if dynamic_meta else {}),
            }
        ]
        for child in children:
            rendered.extend(
                _render_outline_tree_node(
                    child,
                    params,
                    warnings,
                    db_path=db_path,
                    nl2sql_runner=nl2sql_runner,
                    ai_synthesis_runner=ai_synthesis_runner,
                    freeform_runner=freeform_runner,
                )
            )
        return rendered

    if node.get("section_kind") == "structured_leaf" and isinstance(node.get("content"), dict):
        locals_ctx = _locals_from_dynamic_meta(dynamic_meta)
        content, debug, data_status = _render_content(
            node.get("content"),
            params,
            locals_ctx,
            warnings,
            db_path=db_path,
            nl2sql_runner=nl2sql_runner,
            ai_synthesis_runner=ai_synthesis_runner,
        )
        debug["outline_node"] = copy.deepcopy(node)
        payload = {
            "title": title,
            "description": description,
            "content": content,
            "status": "generated" if data_status == "success" else "failed",
            "data_status": data_status,
            "debug": debug,
            "level": level,
        }
        if dynamic_meta:
            payload["dynamic_meta"] = dynamic_meta
        return [payload]

    result = (
        freeform_runner(
            title=title,
            description=description,
            level=level,
            dynamic_meta=dynamic_meta or {},
            outline_node=copy.deepcopy(node),
            params=params,
        )
        if freeform_runner
        else {
            "content": f"{'#' * level} {title}\n\n{description}".strip(),
            "debug": {},
            "status": "generated",
            "data_status": "success",
        }
    )
    debug = dict(result.get("debug") or {})
    debug["outline_node"] = copy.deepcopy(node)
    payload = {
        "title": title,
        "description": description,
        "content": str(result.get("content") or ""),
        "status": str(result.get("status") or "generated"),
        "data_status": str(result.get("data_status") or "success"),
        "debug": debug,
        "level": level,
    }
    if dynamic_meta:
        payload["dynamic_meta"] = dynamic_meta
    return [payload]


def _render_content(
    content: Any,
    params: Dict[str, Any],
    locals_ctx: Dict[str, Any],
    warnings: List[str],
    *,
    db_path: str,
    nl2sql_runner: Optional[Callable[..., Dict[str, Any]]],
    ai_synthesis_runner: Optional[Callable[..., str]],
) -> Tuple[str, Dict[str, Any], str]:
    if not isinstance(content, dict):
        return "", {}, "success"

    normalized_content = _normalize_content(content)
    presentation = normalized_content.get("presentation") if isinstance(normalized_content.get("presentation"), dict) else {}
    presentation_type = str(presentation.get("type") or "")
    dataset_results = _execute_datasets(
        normalized_content.get("datasets"),
        params,
        locals_ctx,
        warnings,
        db_path=db_path,
        nl2sql_runner=nl2sql_runner,
        ai_synthesis_runner=ai_synthesis_runner,
    )

    debug = {
        "datasets": [_dataset_debug_payload(item) for item in dataset_results.values()],
        "render_bindings": [],
    }
    primary_dataset = _pick_primary_dataset(dataset_results)

    if presentation_type == "text":
        template = str(presentation.get("template") or "")
        if template:
            content_text = _render_text(template, params, locals_ctx)
        else:
            content_text = str(primary_dataset.get("text") or _first_dataset_text(dataset_results))
        data_status = "success" if content_text or not dataset_results else _dataset_status(dataset_results)
        debug["render_bindings"] = _bound_dataset_ids(dataset_results)
        return content_text, debug, data_status

    if presentation_type == "value":
        anchor = str(presentation.get("anchor") or "{$value}")
        value = ""
        if primary_dataset.get("rows") and primary_dataset.get("columns"):
            value = primary_dataset["rows"][0].get(primary_dataset["columns"][0], "")
        content_text = anchor.replace("{$value}", _stringify(value))
        debug["render_bindings"] = _bound_dataset_ids(dataset_results)
        return content_text, debug, _dataset_status(dataset_results)

    if presentation_type == "simple_table":
        rows = primary_dataset.get("rows") or []
        columns = primary_dataset.get("columns") or []
        debug["render_bindings"] = _bound_dataset_ids(dataset_results)
        return _render_table(columns, rows), debug, _dataset_status(dataset_results)

    if presentation_type == "chart":
        rows = primary_dataset.get("rows") or []
        columns = primary_dataset.get("columns") or []
        chart_type = str(presentation.get("chart_type") or "chart")
        table = _render_table(columns, rows)
        debug["render_bindings"] = _bound_dataset_ids(dataset_results)
        return f"[chart:{chart_type}]\n\n{table}", debug, _dataset_status(dataset_results)

    if presentation_type == "composite_table":
        debug["render_bindings"] = _composite_bound_dataset_ids(presentation)
        return _render_composite_table(presentation, dataset_results, params, locals_ctx), debug, _dataset_status(dataset_results)

    return "", debug, _dataset_status(dataset_results)


def _execute_datasets(
    datasets: Any,
    params: Dict[str, Any],
    locals_ctx: Dict[str, Any],
    warnings: List[str],
    *,
    db_path: str,
    nl2sql_runner: Optional[Callable[..., Dict[str, Any]]],
    ai_synthesis_runner: Optional[Callable[..., str]],
) -> Dict[str, Dict[str, Any]]:
    items = _as_list(datasets)
    if not items:
        return {}

    remaining = [item for item in items if isinstance(item, dict)]
    results: Dict[str, Dict[str, Any]] = {}

    while remaining:
        progressed = False
        next_remaining: List[Dict[str, Any]] = []
        for dataset in remaining:
            dataset_id = str(dataset.get("id") or "").strip()
            depends_on = [str(item).strip() for item in _as_list(dataset.get("depends_on")) if str(item).strip()]
            if not dataset_id:
                warnings.append("存在缺少 id 的 dataset，已跳过。")
                continue
            if any(dep not in results for dep in depends_on):
                next_remaining.append(dataset)
                continue
            results[dataset_id] = _execute_dataset(
                dataset,
                params,
                locals_ctx,
                warnings,
                dataset_results=results,
                db_path=db_path,
                nl2sql_runner=nl2sql_runner,
                ai_synthesis_runner=ai_synthesis_runner,
            )
            progressed = True

        if progressed:
            remaining = next_remaining
            continue

        unresolved = [str(item.get("id") or "") for item in next_remaining]
        warnings.append(f"检测到 dataset 依赖环或缺失依赖，已跳过：{', '.join(unresolved)}")
        for dataset in next_remaining:
            dataset_id = str(dataset.get("id") or "").strip() or "unknown"
            results[dataset_id] = {
                "dataset_id": dataset_id,
                "status": "failed",
                "kind": str(dataset.get("source", {}).get("kind") or ""),
                "depends_on": [str(item).strip() for item in _as_list(dataset.get("depends_on")) if str(item).strip()],
                "rows": [],
                "columns": [],
                "text": "",
                "debug": {"error_message": "dataset 依赖无法解析"},
            }
        break

    return results


def _execute_dataset(
    dataset: Dict[str, Any],
    params: Dict[str, Any],
    locals_ctx: Dict[str, Any],
    warnings: List[str],
    *,
    dataset_results: Dict[str, Dict[str, Any]],
    db_path: str,
    nl2sql_runner: Optional[Callable[..., Dict[str, Any]]],
    ai_synthesis_runner: Optional[Callable[..., str]],
) -> Dict[str, Any]:
    dataset_id = str(dataset.get("id") or "").strip()
    source = dataset.get("source") if isinstance(dataset.get("source"), dict) else {}
    kind = str(source.get("kind") or "")
    depends_on = [str(item).strip() for item in _as_list(dataset.get("depends_on")) if str(item).strip()]

    base = {
        "dataset_id": dataset_id,
        "status": "success",
        "kind": kind,
        "depends_on": depends_on,
        "rows": [],
        "columns": [],
        "text": "",
        "debug": {},
    }

    if kind == "sql":
        result = _run_sql_source(source, params, locals_ctx, warnings, db_path=db_path)
        base["rows"] = result["rows"]
        base["columns"] = result["columns"]
        base["debug"] = result["debug"]
        base["status"] = result["status"]
        return base

    if kind == "nl2sql":
        result = _run_nl2sql_source(
            source,
            params,
            locals_ctx,
            warnings,
            runner=nl2sql_runner,
            dataset_results=dataset_results,
        )
        base["rows"] = result["rows"]
        base["columns"] = result["columns"]
        base["debug"] = result["debug"]
        base["status"] = result["status"]
        return base

    if kind == "ai_synthesis":
        result = _run_ai_synthesis_source(
            source,
            params,
            locals_ctx,
            warnings,
            dataset_results=dataset_results,
            db_path=db_path,
            ai_synthesis_runner=ai_synthesis_runner,
        )
        base["rows"] = result["rows"]
        base["columns"] = result["columns"]
        base["text"] = result["text"]
        base["debug"] = result["debug"]
        base["status"] = result["status"]
        return base

    warnings.append(f"dataset {dataset_id} 使用了不支持的 kind: {kind}")
    base["status"] = "failed"
    base["debug"] = {"error_message": f"不支持的 dataset kind: {kind}"}
    return base


def _run_sql_source(
    source: Dict[str, Any],
    params: Dict[str, Any],
    locals_ctx: Dict[str, Any],
    warnings: List[str],
    *,
    db_path: str,
) -> Dict[str, Any]:
    query = str(source.get("query") or "")
    if not query:
        warnings.append("SQL source 缺少 query。")
        return {"rows": [], "columns": [], "debug": {}, "status": "failed"}

    compiled = _render_sql(query, params, locals_ctx)
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(compiled)
        rows = [dict(row) for row in cursor.fetchall()]
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()
        debug = {
            "compiled_sql": compiled,
            "row_count": len(rows),
            "sample_rows": rows[:5],
        }
        return {"rows": rows, "columns": columns, "debug": debug, "status": "success"}
    except sqlite3.Error as exc:
        warnings.append(f"SQL 执行失败: {exc}")
        return {
            "rows": [],
            "columns": [],
            "debug": {"compiled_sql": compiled, "error_message": str(exc)},
            "status": "failed",
        }


def _run_nl2sql_source(
    source: Dict[str, Any],
    params: Dict[str, Any],
    locals_ctx: Dict[str, Any],
    warnings: List[str],
    *,
    runner: Optional[Callable[..., Dict[str, Any]]],
    dataset_results: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    if runner is None:
        warnings.append("nl2sql 未配置执行器。")
        return {"rows": [], "columns": [], "debug": {}, "status": "failed"}
    description = _render_text(str(source.get("description") or ""), params, locals_ctx)
    result = runner(
        description=description,
        params=params,
        locals_ctx=locals_ctx,
        dataset_results=dataset_results,
    )
    rows = result.get("rows") or []
    columns = result.get("columns") or (list(rows[0].keys()) if rows else [])
    debug = result.get("debug") or {}
    status = result.get("status") or "success"
    return {
        "rows": rows,
        "columns": columns,
        "debug": debug,
        "status": status,
    }


def _run_ai_synthesis_source(
    source: Dict[str, Any],
    params: Dict[str, Any],
    locals_ctx: Dict[str, Any],
    warnings: List[str],
    *,
    dataset_results: Dict[str, Dict[str, Any]],
    db_path: str,
    ai_synthesis_runner: Optional[Callable[..., str]],
) -> Dict[str, Any]:
    if ai_synthesis_runner is None:
        warnings.append("ai_synthesis 未配置执行器。")
        return {"rows": [], "columns": [], "text": "", "debug": {}, "status": "failed"}

    refs = [str(item).strip() for item in _as_list(source.get("context", {}).get("refs")) if str(item).strip()]
    queries = _as_list(source.get("context", {}).get("queries"))
    query_results = []
    for query in queries:
        if not isinstance(query, dict):
            continue
        query_id = str(query.get("id") or "").strip() or "query"
        sql = str(query.get("query") or "").strip()
        result = _run_sql_source({"kind": "sql", "query": sql}, params, locals_ctx, warnings, db_path=db_path)
        query_results.append(
            {
                "id": query_id,
                "rows": result.get("rows") or [],
                "columns": result.get("columns") or [],
                "debug": result.get("debug") or {},
            }
        )

    prompt = _render_text(str(source.get("prompt") or ""), params, locals_ctx)
    text = str(
        ai_synthesis_runner(
            prompt=prompt,
            params=params,
            locals_ctx=locals_ctx,
            dataset_results=dataset_results,
            refs={key: dataset_results.get(key) for key in refs},
            queries=query_results,
            knowledge=source.get("knowledge") or {},
        )
        or ""
    )
    rows = [{"text": text}] if text else []
    return {
        "rows": rows,
        "columns": ["text"] if text else [],
        "text": text,
        "debug": {
            "refs": refs,
            "queries": query_results,
            "knowledge": source.get("knowledge") or {},
            "prompt": prompt,
        },
        "status": "success" if text else "failed",
    }


def _render_composite_table(
    presentation: Dict[str, Any],
    dataset_results: Dict[str, Dict[str, Any]],
    params: Dict[str, Any],
    locals_ctx: Dict[str, Any],
) -> str:
    sections = _as_list(presentation.get("sections"))
    lines: List[str] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        band = str(section.get("band") or "").strip()
        if band:
            lines.append(f"**{band}**")
        layout = section.get("layout") if isinstance(section.get("layout"), dict) else {}
        dataset = dataset_results.get(str(section.get("dataset_id") or "").strip()) or {}
        layout_type = layout.get("type")
        if layout_type == "kv_grid":
            lines.append(_render_kv_grid(layout, dataset, params, locals_ctx, section))
        elif layout_type == "tabular":
            lines.append(_render_tabular(layout, dataset))
    return "\n\n".join([line for line in lines if line])


def _render_kv_grid(
    layout: Dict[str, Any],
    dataset: Dict[str, Any],
    params: Dict[str, Any],
    locals_ctx: Dict[str, Any],
    section: Dict[str, Any],
) -> str:
    fields = _as_list(layout.get("fields")) or _as_list(section.get("fields"))
    rows: List[Tuple[str, str]] = []
    source = dataset.get("source") if isinstance(dataset.get("source"), dict) else {}
    source_rows = dataset.get("rows") or []
    key_col = source.get("key_col")
    value_col = source.get("value_col")

    if key_col and value_col and source_rows:
        for row in source_rows:
            rows.append((str(row.get(key_col, "")), _stringify(row.get(value_col, ""))))
    else:
        first_row = source_rows[0] if source_rows else {}
        for field in fields:
            if not isinstance(field, dict):
                continue
            key = _render_text(str(field.get("key") or ""), params, locals_ctx)
            if "value" in field:
                value = _render_text(str(field.get("value") or ""), params, locals_ctx)
            elif "col" in field:
                value = _stringify(first_row.get(field.get("col")))
            else:
                value = ""
            rows.append((key, value))

    return _render_table(["key", "value"], [{"key": k, "value": v} for k, v in rows])


def _render_tabular(layout: Dict[str, Any], dataset: Dict[str, Any]) -> str:
    rows = dataset.get("rows") or []
    headers = _as_list(layout.get("headers"))
    columns_cfg = _as_list(layout.get("columns"))
    dataset_columns = list(dataset.get("columns") or [])

    if headers and columns_cfg:
        columns: List[str] = []
        labels: List[str] = []
        used_fields = {str(item.get("field") or "") for item in columns_cfg if str(item.get("field") or "") != "~dynamic~"}
        dynamic_fields = [field for field in dataset_columns if field not in used_fields]
        for index, item in enumerate(columns_cfg):
            field = str(item.get("field") or "")
            header = headers[index] if index < len(headers) and isinstance(headers[index], dict) else {}
            if field == "~dynamic~" and item.get("repeat"):
                for dynamic in dynamic_fields:
                    columns.append(dynamic)
                    labels.append(dynamic)
            else:
                columns.append(field)
                labels.append(str(header.get("label") or field))
        return _render_table_with_mapping(labels, columns, rows)

    if headers:
        labels = [str(item.get("label") or "") for item in headers if isinstance(item, dict)]
        return _render_table(labels, rows)

    return _render_table(dataset_columns, rows)


def _render_table(columns: List[str], rows: List[Dict[str, Any]]) -> str:
    if not columns:
        return ""
    header_line = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join(["---"] * len(columns)) + " |"
    lines = [header_line, divider]
    for row in rows:
        line = "| " + " | ".join(_stringify(row.get(col, "")) for col in columns) + " |"
        lines.append(line)
    return "\n".join(lines)


def _render_table_with_mapping(labels: List[str], columns: List[str], rows: List[Dict[str, Any]]) -> str:
    if not labels or not columns:
        return ""
    header_line = "| " + " | ".join(labels) + " |"
    divider = "| " + " | ".join(["---"] * len(labels)) + " |"
    lines = [header_line, divider]
    for row in rows:
        line = "| " + " | ".join(_stringify(row.get(col, "")) for col in columns) + " |"
        lines.append(line)
    return "\n".join(lines)


def _normalize_content(content: Dict[str, Any]) -> Dict[str, Any]:
    normalized = copy.deepcopy(content)
    if "datasets" in normalized:
        return normalized

    legacy_source = normalized.pop("source", None)
    if isinstance(legacy_source, dict):
        normalized["datasets"] = [{"id": "ds_main", "source": legacy_source}]
    return normalized


def _pick_primary_dataset(dataset_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    if not dataset_results:
        return {}
    return next(iter(dataset_results.values()))


def _first_dataset_text(dataset_results: Dict[str, Dict[str, Any]]) -> str:
    for item in dataset_results.values():
        text = str(item.get("text") or "")
        if text:
            return text
    return ""


def _dataset_status(dataset_results: Dict[str, Dict[str, Any]]) -> str:
    if any(item.get("status") != "success" for item in dataset_results.values()):
        return "failed"
    return "success"


def _dataset_debug_payload(dataset: Dict[str, Any]) -> Dict[str, Any]:
    debug = dataset.get("debug") or {}
    return {
        "dataset_id": dataset.get("dataset_id") or "",
        "kind": dataset.get("kind") or "",
        "depends_on": dataset.get("depends_on") or [],
        "compiled_sql": debug.get("compiled_sql") or "",
        "row_count": debug.get("row_count") or len(dataset.get("rows") or []),
        "sample_rows": debug.get("sample_rows") or (dataset.get("rows") or [])[:5],
        "error_message": debug.get("error_message") or "",
    }


def _bound_dataset_ids(dataset_results: Dict[str, Dict[str, Any]]) -> List[str]:
    return [str(item.get("dataset_id") or "") for item in dataset_results.values()]


def _composite_bound_dataset_ids(presentation: Dict[str, Any]) -> List[str]:
    bound: List[str] = []
    for section in _as_list(presentation.get("sections")):
        if not isinstance(section, dict):
            continue
        dataset_id = str(section.get("dataset_id") or "").strip()
        if dataset_id:
            bound.append(dataset_id)
    return bound


def _render_text(text: str, params: Dict[str, Any], locals_ctx: Dict[str, Any]) -> str:
    def replace_param(match: re.Match) -> str:
        key = match.group(1)
        value = params.get(key)
        return _stringify(value)

    def replace_local(match: re.Match) -> str:
        key = match.group(1)
        value = locals_ctx.get(key)
        return _stringify(value)

    text = re.sub(r"\{([a-zA-Z0-9_]+)\}", replace_param, text)
    text = re.sub(r"\{\$([a-zA-Z0-9_]+)\}", replace_local, text)
    return text


def _dynamic_meta_from_locals(locals_ctx: Dict[str, Any]) -> Dict[str, Any] | None:
    value = locals_ctx.get("__dynamic_meta__")
    if isinstance(value, dict):
        return copy.deepcopy(value)
    return None


def _locals_from_dynamic_meta(dynamic_meta: Dict[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(dynamic_meta, dict):
        return {}
    item_alias = str(dynamic_meta.get("item_alias") or "item")
    index_alias = str(dynamic_meta.get("index_alias") or "index")
    item = dynamic_meta.get("item")
    index = dynamic_meta.get("index")
    locals_ctx: Dict[str, Any] = {
        item_alias: item,
        index_alias: index,
    }
    if item_alias != "item":
        locals_ctx["item"] = item
    if index_alias != "index":
        locals_ctx["index"] = index
    return locals_ctx


def _outline_display_text(title: Any, description: Any) -> str:
    title_text = str(title or "").strip()
    description_text = str(description or "").strip()
    if title_text and description_text:
        return f"{title_text}：{description_text}"
    return title_text or description_text


def _content_uses_ai(content: Dict[str, Any]) -> bool:
    for dataset in _as_list(content.get("datasets")):
        if not isinstance(dataset, dict):
            continue
        source = dataset.get("source") if isinstance(dataset.get("source"), dict) else {}
        kind = str(source.get("kind") or "").strip()
        if kind in {"nl2sql", "ai_synthesis"}:
            return True
    return False


def _render_sql(sql: str, params: Dict[str, Any], locals_ctx: Dict[str, Any]) -> str:
    def replace_param(match: re.Match) -> str:
        key = match.group(1)
        return _sql_literal(params.get(key))

    def replace_local(match: re.Match) -> str:
        key = match.group(1)
        return _sql_literal(locals_ctx.get(key))

    sql = re.sub(r"\{([a-zA-Z0-9_]+)\}", replace_param, sql)
    sql = re.sub(r"\{\$([a-zA-Z0-9_]+)\}", replace_local, sql)
    return sql


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, list):
        return ", ".join(_sql_literal(item) for item in value)
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except ValueError:
            return []
        return loaded if isinstance(loaded, list) else []
    return []
