from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Dict, Iterable, List

import ibis

from .ai_gateway import AIRequestError, OpenAICompatGateway, ProviderConfig
from .telecom_demo_service import get_demo_db_path, get_schema_registry_text, open_demo_connection

MAX_QUERY_RETRIES = 3
MAX_SAMPLE_ROWS = 10
MAX_CONTEXT_ROWS = 3
MAX_RESULT_ROWS_HINT = 50

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


class SectionQueryError(Exception):
    pass


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


def generate_section_evidence(
    *,
    gateway: OpenAICompatGateway,
    config: ProviderConfig,
    template_context: Dict[str, Any],
    section: Dict[str, Any],
    params: Dict[str, Any],
) -> Dict[str, Any]:
    title = str(section.get("title") or "未命名章节").strip()
    description = str(section.get("description") or "").strip()
    dynamic_meta = section.get("dynamic_meta") if isinstance(section.get("dynamic_meta"), dict) else None
    query_hint = str(section.get("data_query_hint") or "").strip()
    nl_request = _build_nl_request(template_context, section, params, query_hint, dynamic_meta)

    last_error = ""
    last_code = ""
    last_sql = ""
    attempts = 0

    for attempt in range(1, MAX_QUERY_RETRIES + 1):
        attempts = attempt
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
                {"role": "user", "content": _build_query_prompt(nl_request, last_error)},
            ],
            temperature=min(config.temperature, 0.1),
            max_tokens=900,
        )
        last_code = _extract_code_block(response["content"])
        try:
            execution = execute_ibis_code(last_code)
            return {
                "title": title,
                "description": description,
                "level": max(1, min(6, int(section.get("level") or 1))),
                "dynamic_meta": dynamic_meta,
                "data_status": "success",
                "status": "generated",
                "debug": {
                    "nl_request": nl_request,
                    "ibis_code": execution.ibis_code,
                    "compiled_sql": execution.compiled_sql,
                    "attempts": attempts,
                    "row_count": execution.row_count,
                    "sample_rows": execution.sample_rows,
                    "error_message": "",
                },
                "query_model": response["model"],
            }
        except SectionQueryError as exc:
            last_error = str(exc)
            last_sql = _extract_sql_from_error(last_error, last_sql)

    return {
        "title": title,
        "description": description,
        "level": max(1, min(6, int(section.get("level") or 1))),
        "dynamic_meta": dynamic_meta,
        "data_status": "failed",
        "status": "failed",
        "debug": {
            "nl_request": nl_request,
            "ibis_code": last_code,
            "compiled_sql": last_sql,
            "attempts": attempts,
            "row_count": 0,
            "sample_rows": [],
            "error_message": last_error or "未生成出可执行查询。",
        },
        "query_model": config.model,
    }


def execute_ibis_code(code: str) -> QueryExecutionResult:
    sanitized = _extract_code_block(code)
    if not sanitized.strip():
        raise SectionQueryError("模型没有返回 Ibis 代码。")

    tree = ast.parse(sanitized, mode="exec")
    validator = IbisAstValidator()
    validator.validate(tree)

    backend = ibis.sqlite.connect(get_demo_db_path())
    tables = MappingProxyType({name: backend.table(name) for name in backend.list_tables()})
    globals_env = {
        "__builtins__": {},
        "ibis": SafeIbis(),
        "tables": tables,
    }
    locals_env: Dict[str, Any] = {}
    try:
        exec(compile(tree, "<generated_ibis>", "exec"), globals_env, locals_env)
    except Exception as exc:
        raise SectionQueryError(f"Ibis 代码执行失败：{exc}") from exc

    result = locals_env.get("result")
    if result is None:
        raise SectionQueryError("Ibis 代码必须把最终结果赋值到 result。")
    if not hasattr(result, "as_table"):
        raise SectionQueryError("result 必须是 Ibis 表达式。")

    try:
        table_expr = result.as_table()
        compiled_sql = str(backend.compile(table_expr)).strip()
    except Exception as exc:
        raise SectionQueryError(f"Ibis 编译 SQL 失败：{exc}") from exc

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
        raise SectionQueryError(f"SQL 执行失败：{exc} | SQL: {compiled_sql}") from exc

    return QueryExecutionResult(
        ibis_code=sanitized.strip(),
        compiled_sql=compiled_sql,
        row_count=row_count,
        sample_rows=sample_rows,
    )


def build_report_context(section_results: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    successful: List[Dict[str, Any]] = []
    failed: List[str] = []
    for item in section_results:
        debug = item.get("debug") if isinstance(item.get("debug"), dict) else {}
        if item.get("data_status") == "success":
            successful.append(
                {
                    "title": item.get("title") or "未命名章节",
                    "row_count": int(debug.get("row_count") or 0),
                    "sample_rows": list(debug.get("sample_rows") or [])[:MAX_CONTEXT_ROWS],
                }
            )
        else:
            failed.append(str(item.get("title") or "未命名章节"))
    return {
        "successful_sections": len(successful),
        "failed_sections": len(failed),
        "highlights": successful[:8],
        "failed_titles": failed[:8],
    }


def _build_nl_request(
    template_context: Dict[str, Any],
    section: Dict[str, Any],
    params: Dict[str, Any],
    query_hint: str,
    dynamic_meta: Dict[str, Any] | None,
) -> str:
    lines = [
        f"模板名称：{template_context.get('name') or '未命名模板'}",
        f"模板描述：{template_context.get('description') or '未提供'}",
        f"报告类型：{template_context.get('report_type') or '未提供'}",
        f"场景：{template_context.get('scenario') or '未提供'}",
        f"章节标题：{section.get('title') or '未命名章节'}",
        f"章节描述：{section.get('description') or '未提供'}",
        "用户输入参数(JSON)：",
        json.dumps(params or {}, ensure_ascii=False, indent=2, default=str),
    ]
    if template_context.get("content_params"):
        lines.extend(
            [
                "模板参数定义(JSON)：",
                json.dumps(template_context.get("content_params") or [], ensure_ascii=False, indent=2, default=str),
            ]
        )
    if dynamic_meta:
        lines.extend(
            [
                "动态章节上下文(JSON)：",
                json.dumps(dynamic_meta, ensure_ascii=False, indent=2, default=str),
            ]
        )
    if query_hint:
        lines.append(f"章节查询提示：{query_hint}")
    lines.append("目标：生成一个最能支撑该章节写作的数据查询。")
    return "\n".join(lines)


def _build_query_prompt(nl_request: str, last_error: str) -> str:
    retry_hint = ""
    if last_error:
        retry_hint = (
            "\n上一次生成失败，失败原因如下，请修正：\n"
            f"{last_error}\n"
        )
    return "\n".join(
        [
            nl_request,
            retry_hint,
            get_schema_registry_text(),
            "约束：",
            f"1. 只能使用 tables[\"表名\"] 访问数据表，只能使用上面列出的 10 张表。",
            f"2. 只能使用 ibis 以及 Ibis 表达式常见方法：filter/select/mutate/group_by/aggregate/order_by/limit/join。",
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


def _extract_code_block(text: str) -> str:
    content = str(text or "").strip()
    fenced = re.findall(r"```(?:python)?\s*(.*?)```", content, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        return fenced[0].strip()
    return content


def _extract_sql_from_error(error_message: str, current: str) -> str:
    match = re.search(r"SQL:\s*(SELECT.+)$", error_message, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return current


def _coerce_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: _coerce_value(value)
        for key, value in dict(row).items()
    }


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
            raise SectionQueryError("Ibis 代码必须定义 result 变量。")

    def generic_visit(self, node: ast.AST) -> None:
        if isinstance(node, _DISALLOWED_AST_NODES):
            raise SectionQueryError(f"不允许的 Python 语法：{type(node).__name__}")
        super().generic_visit(node)

    def visit_Module(self, node: ast.Module) -> None:
        if not node.body:
            raise SectionQueryError("Ibis 代码不能为空。")
        if len(node.body) > 24:
            raise SectionQueryError("Ibis 代码过长，请只保留必要步骤。")
        for stmt in node.body:
            if not isinstance(stmt, (ast.Assign, ast.Expr)):
                raise SectionQueryError("Ibis 代码只能包含赋值语句或简单表达式。")
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if not isinstance(target, ast.Name):
                raise SectionQueryError("只允许把表达式赋值给简单变量名。")
            if target.id in _DISALLOWED_NAMES or target.id.startswith("_"):
                raise SectionQueryError(f"不允许的变量名：{target.id}")
            self._locals.add(target.id)
        self.visit(node.value)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            return
        if node.id in {"True", "False", "None"}:
            return
        if node.id in _DISALLOWED_NAMES or node.id.startswith("__"):
            raise SectionQueryError(f"不允许访问名称：{node.id}")
        if node.id not in {"tables", "ibis"} and node.id not in self._locals:
            raise SectionQueryError(f"引用了未定义名称：{node.id}")

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("_"):
            raise SectionQueryError(f"不允许访问私有属性：{node.attr}")
        self.visit(node.value)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            if node.func.id not in self._locals:
                raise SectionQueryError(f"不允许直接调用函数：{node.func.id}")
        elif isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "ibis":
                if attr not in _ALLOWED_IBIS_FUNCS:
                    raise SectionQueryError(f"不允许调用 ibis.{attr}")
            elif attr not in _ALLOWED_METHODS:
                raise SectionQueryError(f"不允许调用方法：{attr}")
            self.visit(node.func.value)
        else:
            raise SectionQueryError("不允许动态调用。")
        for arg in node.args:
            self.visit(arg)
        for keyword in node.keywords:
            self.visit(keyword.value)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if isinstance(node.value, ast.Name) and node.value.id == "tables":
            if not isinstance(node.slice, ast.Constant) or not isinstance(node.slice.value, str):
                raise SectionQueryError('访问 tables 时必须使用字符串字面量，例如 tables["dim_site"]。')
        self.visit(node.value)
        self.visit(node.slice)

