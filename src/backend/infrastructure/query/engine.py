from __future__ import annotations

import ast
import json
import os
import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Iterable, List, Mapping

import ibis

from ..ai.openai_compat import OpenAICompatGateway, ProviderConfig
from ..demo.telecom import (
    get_demo_db_path,
    get_schema_registry,
    get_schema_registry_text,
    open_demo_connection,
)

MAX_QUERY_RETRIES = 3
MAX_SAMPLE_ROWS = 10
MAX_RESULT_ROWS_HINT = 50
DEFAULT_QUERY_STRATEGY = "legacy"
VALID_QUERY_STRATEGIES = {"legacy", "ibis_planner"}

_ALLOWED_METHODS = {
    "aggregate",
    "asc",
    "between",
    "cast",
    "count",
    "desc",
    "distinct",
    "fill_null",
    "filter",
    "group_by",
    "inner_join",
    "isin",
    "join",
    "left_join",
    "limit",
    "lower",
    "max",
    "mean",
    "min",
    "mutate",
    "notnull",
    "nunique",
    "order_by",
    "round",
    "select",
    "sum",
    "upper",
}
_ALLOWED_IBIS_FUNCS = {"asc", "coalesce", "desc", "literal"}
_DISALLOWED_NAMES = {
    "__builtins__",
    "__class__",
    "__dict__",
    "__import__",
    "__mro__",
    "__subclasses__",
    "eval",
    "exec",
    "globals",
    "locals",
    "open",
}
_DISALLOWED_AST_NODES = (
    ast.AsyncFor,
    ast.AsyncFunctionDef,
    ast.AsyncWith,
    ast.Await,
    ast.ClassDef,
    ast.Delete,
    ast.For,
    ast.FunctionDef,
    ast.Global,
    ast.Import,
    ast.ImportFrom,
    ast.Lambda,
    ast.Nonlocal,
    ast.Raise,
    ast.Try,
    ast.While,
    ast.With,
    ast.Yield,
    ast.YieldFrom,
)


class QueryEngineError(Exception):
    def __init__(self, stage: str, message: str):
        super().__init__(message)
        self.stage = stage
        self.message = message


@dataclass
class QueryRequest:
    nl_request: str
    template_context: Dict[str, Any]
    section: Dict[str, Any]
    params: Dict[str, Any]
    query_hint: str = ""
    dynamic_meta: Dict[str, Any] | None = None


@dataclass
class QuerySpec:
    intent: str = ""
    tables: List[str] = field(default_factory=list)
    joins: List[Dict[str, Any]] = field(default_factory=list)
    dimensions: List[str] = field(default_factory=list)
    measures: List[str] = field(default_factory=list)
    filters: List[Dict[str, Any]] = field(default_factory=list)
    sort: List[Dict[str, Any]] = field(default_factory=list)
    limit: int | None = None
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "tables": list(self.tables),
            "joins": list(self.joins),
            "dimensions": list(self.dimensions),
            "measures": list(self.measures),
            "filters": list(self.filters),
            "sort": list(self.sort),
            "limit": self.limit,
            "notes": list(self.notes),
            "warnings": list(self.warnings),
        }


@dataclass
class QueryDebugTrace:
    strategy: str
    nl_request: str
    schema_candidates: List[Dict[str, Any]] = field(default_factory=list)
    query_spec: Dict[str, Any] = field(default_factory=dict)
    ibis_code: str = ""
    compiled_sql: str = ""
    attempts: int = 0
    row_count: int = 0
    sample_rows: List[Dict[str, Any]] = field(default_factory=list)
    error_stage: str = ""
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "nl_request": self.nl_request,
            "schema_candidates": list(self.schema_candidates),
            "query_spec": dict(self.query_spec),
            "ibis_code": self.ibis_code,
            "compiled_sql": self.compiled_sql,
            "attempts": self.attempts,
            "row_count": self.row_count,
            "sample_rows": list(self.sample_rows),
            "error_stage": self.error_stage,
            "error_message": self.error_message,
        }


@dataclass
class QueryRunResult:
    success: bool
    model: str
    compiled_sql: str
    sample_rows: List[Dict[str, Any]]
    row_count: int
    debug: Dict[str, Any]


@dataclass
class QueryExecutionResult:
    ibis_code: str
    compiled_sql: str
    row_count: int
    sample_rows: List[Dict[str, Any]]


class SafeIbis:
    asc = staticmethod(ibis.asc)
    coalesce = staticmethod(ibis.coalesce)
    desc = staticmethod(ibis.desc)
    literal = staticmethod(ibis.literal)


class SqliteCompilerAdapter:
    def __init__(self) -> None:
        self.backend = ibis.sqlite.connect(get_demo_db_path())

    def compile(self, expr: Any) -> str:
        try:
            table_expr = expr.as_table()
            return str(self.backend.compile(table_expr)).strip()
        except Exception as exc:  # pragma: no cover - exercised via caller behavior
            raise QueryEngineError("compile", f"Ibis 编译 SQL 失败：{exc}") from exc

    def normalize(self, sql: str) -> str:
        return re.sub(r"\s+", " ", str(sql or "").strip())


def resolve_query_strategy(explicit: str | None = None) -> str:
    candidate = str(explicit or os.getenv("REPORT_QUERY_STRATEGY") or DEFAULT_QUERY_STRATEGY).strip().lower()
    if candidate not in VALID_QUERY_STRATEGIES:
        return DEFAULT_QUERY_STRATEGY
    return candidate


def run_query(
    *,
    gateway: OpenAICompatGateway,
    config: ProviderConfig,
    request: QueryRequest,
    strategy: str | None = None,
) -> QueryRunResult:
    effective_strategy = resolve_query_strategy(strategy)
    schema_candidates = build_schema_candidates(request)
    debug = QueryDebugTrace(
        strategy=effective_strategy,
        nl_request=request.nl_request,
        schema_candidates=schema_candidates,
    )

    if effective_strategy == "legacy":
        return _run_legacy_query(gateway=gateway, config=config, request=request, debug=debug)
    return _run_ibis_planner_query(gateway=gateway, config=config, request=request, debug=debug)


def build_schema_candidates(request: QueryRequest, *, limit: int = 5) -> List[Dict[str, Any]]:
    corpus = "\n".join(
        [
            str(request.nl_request or ""),
            str((request.section or {}).get("title") or ""),
            str((request.section or {}).get("description") or ""),
            json.dumps(request.params or {}, ensure_ascii=False, default=str),
            str((request.template_context or {}).get("name") or ""),
            str((request.template_context or {}).get("description") or ""),
        ]
    )
    normalized_corpus = _normalize_text(corpus)
    candidates: List[Dict[str, Any]] = []
    for item in get_schema_registry():
        score = 0
        matched_terms: List[str] = []
        search_terms = [item["name"], item.get("description") or ""]
        search_terms.extend(name for name, _col_type, _desc in item.get("columns") or [])
        search_terms.extend(desc for _name, _col_type, desc in item.get("columns") or [])
        for raw_term in search_terms:
            term = str(raw_term or "").strip()
            normalized_term = _normalize_text(term)
            if not normalized_term or len(normalized_term) < 2:
                continue
            if normalized_term in normalized_corpus:
                matched_terms.append(term)
                if term == item["name"]:
                    score += 5
                elif term == item.get("description"):
                    score += 3
                else:
                    score += 1
        candidates.append(
            {
                "table": item["name"],
                "description": item.get("description") or "",
                "score": score,
                "matched_terms": matched_terms[:6],
                "columns": [name for name, _col_type, _desc in item.get("columns") or []],
            }
        )
    candidates.sort(key=lambda value: (-int(value["score"]), str(value["table"])))
    return candidates[:limit]


def _run_legacy_query(
    *,
    gateway: OpenAICompatGateway,
    config: ProviderConfig,
    request: QueryRequest,
    debug: QueryDebugTrace,
) -> QueryRunResult:
    last_error = ""
    last_code = ""
    last_sql = ""
    last_model = config.model
    for attempt in range(1, MAX_QUERY_RETRIES + 1):
        debug.attempts = attempt
        response = gateway.chat_completion(
            config,
            [
                {
                    "role": "system",
                    "content": (
                        "你是电信网络运维数据分析助手，负责把中文查询意图转成可执行的 Ibis Python 代码。"
                        "你只能输出 Python 代码，不要解释，不要 Markdown 围栏。"
                    ),
                },
                {"role": "user", "content": _build_legacy_query_prompt(request.nl_request, last_error)},
            ],
            temperature=min(config.temperature, 0.1),
            max_tokens=900,
        )
        last_model = response["model"]
        last_code = _extract_code_block(response["content"])
        debug.ibis_code = last_code
        try:
            execution = execute_ibis_code(last_code)
            debug.compiled_sql = execution.compiled_sql
            debug.row_count = execution.row_count
            debug.sample_rows = execution.sample_rows
            debug.error_stage = ""
            debug.error_message = ""
            return QueryRunResult(
                success=True,
                model=last_model,
                compiled_sql=execution.compiled_sql,
                sample_rows=execution.sample_rows,
                row_count=execution.row_count,
                debug=debug.to_dict(),
            )
        except QueryEngineError as exc:
            last_error = exc.message
            debug.error_stage = exc.stage
            debug.error_message = exc.message
            last_sql = _extract_sql_from_error(exc.message, last_sql)
            debug.compiled_sql = last_sql
    return QueryRunResult(
        success=False,
        model=last_model,
        compiled_sql=last_sql,
        sample_rows=[],
        row_count=0,
        debug=debug.to_dict(),
    )


def _run_ibis_planner_query(
    *,
    gateway: OpenAICompatGateway,
    config: ProviderConfig,
    request: QueryRequest,
    debug: QueryDebugTrace,
) -> QueryRunResult:
    planner_model = config.model
    try:
        planner_response = gateway.chat_completion(
            config,
            [
                {
                    "role": "system",
                    "content": (
                        "你是查询规划助手。请根据自然语言查询和 schema 候选，输出结构化 QuerySpec JSON。"
                        "不要输出解释，不要输出 Markdown。"
                    ),
                },
                {"role": "user", "content": _build_planner_prompt(request, debug.schema_candidates)},
            ],
            temperature=min(config.temperature, 0.1),
            max_tokens=800,
        )
        planner_model = planner_response["model"]
        query_spec = _parse_query_spec(planner_response["content"])
        debug.query_spec = query_spec.to_dict()
    except QueryEngineError as exc:
        debug.error_stage = exc.stage
        debug.error_message = exc.message
        return QueryRunResult(
            success=False,
            model=planner_model,
            compiled_sql="",
            sample_rows=[],
            row_count=0,
            debug=debug.to_dict(),
        )

    last_error = ""
    last_model = planner_model
    last_sql = ""
    for attempt in range(1, MAX_QUERY_RETRIES + 1):
        debug.attempts = attempt
        response = gateway.chat_completion(
            config,
            [
                {
                    "role": "system",
                    "content": (
                        "你是电信网络运维数据分析助手，负责把 QuerySpec 翻译成可执行的 Ibis Python 代码。"
                        "你只能输出 Python 代码，不要解释，不要 Markdown 围栏。"
                    ),
                },
                {"role": "user", "content": _build_ibis_prompt(request, query_spec, debug.schema_candidates, last_error)},
            ],
            temperature=min(config.temperature, 0.1),
            max_tokens=900,
        )
        last_model = response["model"]
        debug.ibis_code = _extract_code_block(response["content"])
        try:
            execution = execute_ibis_code(debug.ibis_code)
            debug.compiled_sql = execution.compiled_sql
            debug.row_count = execution.row_count
            debug.sample_rows = execution.sample_rows
            debug.error_stage = ""
            debug.error_message = ""
            return QueryRunResult(
                success=True,
                model=last_model,
                compiled_sql=execution.compiled_sql,
                sample_rows=execution.sample_rows,
                row_count=execution.row_count,
                debug=debug.to_dict(),
            )
        except QueryEngineError as exc:
            last_error = exc.message
            debug.error_stage = exc.stage
            debug.error_message = exc.message
            last_sql = _extract_sql_from_error(exc.message, last_sql)
            debug.compiled_sql = last_sql

    return QueryRunResult(
        success=False,
        model=last_model,
        compiled_sql=last_sql,
        sample_rows=[],
        row_count=0,
        debug=debug.to_dict(),
    )


def execute_ibis_code(code: str) -> QueryExecutionResult:
    sanitized = _extract_code_block(code)
    if not sanitized.strip():
        raise QueryEngineError("generation", "模型没有返回 Ibis 代码。")

    tree = ast.parse(sanitized, mode="exec")
    validator = IbisAstValidator()
    validator.validate(tree)

    backend = ibis.sqlite.connect(get_demo_db_path())
    tables = MappingProxyType({name: backend.table(name) for name in backend.list_tables()})
    globals_env = {"__builtins__": {}, "ibis": SafeIbis(), "tables": tables}
    locals_env: Dict[str, Any] = {}
    try:
        exec(compile(tree, "<generated_ibis>", "exec"), globals_env, locals_env)
    except Exception as exc:
        raise QueryEngineError("generation", f"Ibis 代码执行失败：{exc}") from exc

    result = locals_env.get("result")
    if result is None:
        raise QueryEngineError("generation", "Ibis 代码必须把最终结果赋值到 result。")
    if not hasattr(result, "as_table"):
        raise QueryEngineError("generation", "result 必须是 Ibis 表达式。")

    compiler = SqliteCompilerAdapter()
    compiled_sql = compiler.normalize(compiler.compile(result))

    try:
        with open_demo_connection() as conn:
            row_count = int(
                conn.execute(f"SELECT COUNT(*) AS cnt FROM ({compiled_sql}) AS generated_result").fetchone()["cnt"]
            )
            sample_rows = [
                _coerce_row(row)
                for row in conn.execute(
                    f"SELECT * FROM ({compiled_sql}) AS generated_result LIMIT {MAX_SAMPLE_ROWS}"
                ).fetchall()
            ]
    except Exception as exc:
        raise QueryEngineError("execute", f"SQL 执行失败：{exc} | SQL: {compiled_sql}") from exc

    return QueryExecutionResult(
        ibis_code=sanitized.strip(),
        compiled_sql=compiled_sql,
        row_count=row_count,
        sample_rows=sample_rows,
    )


def _build_legacy_query_prompt(nl_request: str, last_error: str) -> str:
    retry_hint = ""
    if last_error:
        retry_hint = f"\n上一次生成失败，失败原因如下，请修正：\n{last_error}\n"
    return "\n".join(
        [
            nl_request,
            retry_hint,
            get_schema_registry_text(),
            "约束：",
            '1. 只能使用 tables["表名"] 访问数据表，只能使用上面列出的 10 张表。',
            "2. 只能使用 ibis 以及 Ibis 表达式常见方法：filter/select/mutate/group_by/aggregate/order_by/limit/join。",
            "3. 必须把最终结果赋值给 result。",
            f"4. 结果优先控制在 {MAX_RESULT_ROWS_HINT} 行以内；做排行时请显式 limit。",
            "5. 如果章节偏总结，也要选择最能支撑结论的一条核心查询，而不是返回整张明细表。",
            "6. 只输出 Python 代码，不要 ```，不要解释。",
            "参考风格：",
            'cells = tables["dim_cell"]',
            'kpi = tables["fact_cell_kpi_daily"]',
            'joined = cells.join(kpi, cells.cell_id == kpi.cell_id)',
            'result = joined.filter(kpi.stat_date == "2026-03-06").group_by(cells.technology).aggregate(avg_prb=kpi.prb_utilization.mean()).order_by(ibis.desc("avg_prb"))',
        ]
    )


def _build_planner_prompt(request: QueryRequest, schema_candidates: List[Dict[str, Any]]) -> str:
    payload = {
        "nl_request": request.nl_request,
        "section": request.section,
        "params": request.params,
        "query_hint": request.query_hint,
        "dynamic_meta": request.dynamic_meta or {},
        "schema_candidates": schema_candidates,
    }
    return "\n".join(
        [
            "请输出一个 QuerySpec JSON，字段固定为：",
            json.dumps(
                {
                    "intent": "query intent",
                    "tables": ["table_a"],
                    "joins": [],
                    "dimensions": [],
                    "measures": [],
                    "filters": [],
                    "sort": [],
                    "limit": 20,
                    "notes": [],
                    "warnings": [],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "输入上下文：",
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            "要求：",
            "1. 只输出合法 JSON。",
            "2. tables 必须优先从 schema_candidates 里选择。",
            "3. 如果查询是明细列表，dimensions 应列出主要字段，measures 可以为空。",
            "4. 如果查询是统计类，measures 必须明确聚合目标。",
            "5. 若信息不足，也要返回最合理的草案，并把不确定点写入 warnings。",
        ]
    )


def _build_ibis_prompt(
    request: QueryRequest,
    query_spec: QuerySpec,
    schema_candidates: List[Dict[str, Any]],
    last_error: str,
) -> str:
    retry_hint = ""
    if last_error:
        retry_hint = f"\n上一次 Ibis 生成失败，失败原因如下，请修正：\n{last_error}\n"
    payload = {
        "nl_request": request.nl_request,
        "query_spec": query_spec.to_dict(),
        "schema_candidates": schema_candidates,
    }
    return "\n".join(
        [
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            retry_hint,
            get_schema_registry_text(),
            "约束：",
            '1. 只能使用 tables["表名"] 访问数据表，只能使用上面列出的 10 张表。',
            "2. 只能使用 ibis 以及 Ibis 表达式常见方法：filter/select/mutate/group_by/aggregate/order_by/limit/join。",
            "3. 必须把最终结果赋值给 result。",
            f"4. 结果优先控制在 {MAX_RESULT_ROWS_HINT} 行以内；做排行时请显式 limit。",
            "5. 优先使用 QuerySpec 中声明的 tables / dimensions / measures / filters / sort / limit。",
            "6. 只输出 Python 代码，不要 ```，不要解释。",
        ]
    )


def _parse_query_spec(text: str) -> QuerySpec:
    raw = _extract_json_block(text)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise QueryEngineError("planning", f"QuerySpec JSON 解析失败：{exc}") from exc
    if not isinstance(payload, dict):
        raise QueryEngineError("planning", "QuerySpec 必须是 JSON 对象。")
    return QuerySpec(
        intent=str(payload.get("intent") or "").strip(),
        tables=_ensure_str_list(payload.get("tables")),
        joins=_ensure_dict_list(payload.get("joins")),
        dimensions=_ensure_str_list(payload.get("dimensions")),
        measures=_ensure_str_list(payload.get("measures")),
        filters=_ensure_dict_list(payload.get("filters")),
        sort=_ensure_dict_list(payload.get("sort")),
        limit=_ensure_int_or_none(payload.get("limit")),
        notes=_ensure_str_list(payload.get("notes")),
        warnings=_ensure_str_list(payload.get("warnings")),
    )


def _ensure_str_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _ensure_dict_list(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _ensure_int_or_none(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return None


def _extract_code_block(text: str) -> str:
    content = str(text or "").strip()
    fenced = re.findall(r"```(?:python)?\s*(.*?)```", content, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        return fenced[0].strip()
    return content


def _extract_json_block(text: str) -> str:
    content = str(text or "").strip()
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", content, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        return fenced[0].strip()
    start = content.find("{")
    end = content.rfind("}")
    if start >= 0 and end > start:
        return content[start : end + 1]
    return content


def _extract_sql_from_error(error_message: str, current: str) -> str:
    match = re.search(r"SQL:\s*(SELECT.+)$", error_message, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return current


def _normalize_text(text: str) -> str:
    lowered = str(text or "").lower()
    return re.sub(r"[\s_\-:：,，。/\\()（）\"'`]+", "", lowered)


def _coerce_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: _coerce_value(value) for key, value in dict(row).items()}


def _coerce_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            return str(value)
    return value


class IbisAstValidator(ast.NodeVisitor):
    def __init__(self) -> None:
        self._locals: set[str] = set()

    def validate(self, tree: ast.AST) -> None:
        self.visit(tree)
        if "result" not in self._locals:
            raise QueryEngineError("generation", "Ibis 代码必须定义 result 变量。")

    def generic_visit(self, node: ast.AST) -> None:
        if isinstance(node, _DISALLOWED_AST_NODES):
            raise QueryEngineError("generation", f"不允许的 Python 语法：{type(node).__name__}")
        super().generic_visit(node)

    def visit_Module(self, node: ast.Module) -> None:
        if not node.body:
            raise QueryEngineError("generation", "Ibis 代码不能为空。")
        if len(node.body) > 24:
            raise QueryEngineError("generation", "Ibis 代码过长，请只保留必要步骤。")
        for stmt in node.body:
            if not isinstance(stmt, (ast.Assign, ast.Expr)):
                raise QueryEngineError("generation", "Ibis 代码只能包含赋值语句或简单表达式。")
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if not isinstance(target, ast.Name):
                raise QueryEngineError("generation", "只允许把表达式赋值给简单变量名。")
            if target.id in _DISALLOWED_NAMES or target.id.startswith("_"):
                raise QueryEngineError("generation", f"不允许的变量名：{target.id}")
            self._locals.add(target.id)
        self.visit(node.value)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            return
        if node.id in {"True", "False", "None"}:
            return
        if node.id in _DISALLOWED_NAMES or node.id.startswith("__"):
            raise QueryEngineError("generation", f"不允许访问名称：{node.id}")
        if node.id not in {"tables", "ibis"} and node.id not in self._locals:
            raise QueryEngineError("generation", f"引用了未定义名称：{node.id}")

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("_"):
            raise QueryEngineError("generation", f"不允许访问私有属性：{node.attr}")
        self.visit(node.value)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            if node.func.id not in self._locals:
                raise QueryEngineError("generation", f"不允许直接调用函数：{node.func.id}")
        elif isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "ibis":
                if attr not in _ALLOWED_IBIS_FUNCS:
                    raise QueryEngineError("generation", f"不允许调用 ibis.{attr}")
            elif attr not in _ALLOWED_METHODS:
                raise QueryEngineError("generation", f"不允许调用方法：{attr}")
            self.visit(node.func.value)
        else:
            raise QueryEngineError("generation", "不允许动态调用。")
        for arg in node.args:
            self.visit(arg)
        for keyword in node.keywords:
            self.visit(keyword.value)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if isinstance(node.value, ast.Name) and node.value.id == "tables":
            if not isinstance(node.slice, ast.Constant) or not isinstance(node.slice.value, str):
                raise QueryEngineError("generation", '访问 tables 时必须使用字符串字面量，例如 tables["dim_site"]。')
        self.visit(node.value)
        self.visit(node.slice)
