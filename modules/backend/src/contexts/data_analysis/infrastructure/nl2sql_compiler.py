"""Restricted execution and DTE SQL compilation for generated Ibis queries."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import ibis
import ibis.expr.types as ir

from ...._third_party.ibis.ibis_ext import to_sql
from ..application.ports import Nl2SqlCompiler
from ..domain.models import Nl2SqlCompileError, Nl2SqlContext
from .contextvar import current_fk_whitelist, current_table_config
from .data_structure import ForeignKey
from .ibis_tool_functions import create_device2kpi_wide_table, create_recursive_query
from .tools import get_tables_columns


_DISALLOWED_NODES = (
    ast.AsyncFunctionDef,
    ast.Await,
    ast.ClassDef,
    ast.Delete,
    ast.For,
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
_DISALLOWED_NAMES = {
    "__builtins__", "__import__", "breakpoint", "compile", "eval", "exec",
    "getattr", "globals", "help", "input", "locals", "open", "setattr", "vars",
}
_SAFE_GLOBALS = {
    "ibis", "_", "create_recursive_query", "create_device2kpi_wide_table",
    "get_tables_columns",
}
_TYPE_ALIASES = {
    "bool": "boolean", "boolean": "boolean",
    "byte": "int8", "short": "int16", "integer": "int64", "int": "int64",
    "long": "int64", "float": "float64", "double": "float64", "decimal": "float64",
    "date": "date", "time": "time", "timestamp": "timestamp", "datetime": "timestamp",
    "string": "string", "text": "string", "varchar": "string",
}


@dataclass(frozen=True, slots=True)
class QueryConfig:
    """Attribute-only view of the logical entities selected for one generation."""

    _tables: MappingProxyType

    def __getattr__(self, name: str):
        try:
            return self._tables[name]
        except KeyError as exc:
            raise AttributeError(f"Logical entity is not available: {name}") from exc


class RestrictedIbisNl2SqlCompiler(Nl2SqlCompiler):
    def compile(self, *, source: str, context: Nl2SqlContext) -> str:
        tree = _IbisQueryAstValidator().validate(source)
        config = QueryConfig(MappingProxyType(_build_tables(context.entities)))
        relations = tuple(
            relation
            for relation in (ForeignKey.from_mapping(item) for item in context.relations)
            if relation.complete
        )
        namespace: dict[str, Any] = {
            "__builtins__": {},
            "ibis": ibis,
            "_": ibis._,
            "QueryConfig": QueryConfig,
            "Expr": ir.Expr,
            "create_recursive_query": create_recursive_query,
            "create_device2kpi_wide_table": create_device2kpi_wide_table,
            "get_tables_columns": get_tables_columns,
        }
        fk_token = current_fk_whitelist.set(relations)
        config_token = current_table_config.set(config)
        try:
            exec(compile(tree, "<generated-nl2sql>", "exec"), namespace, namespace)
            expression = namespace["query"](config)
        except Exception as exc:
            raise Nl2SqlCompileError("execute", f"Ibis query execution failed: {exc}") from exc
        finally:
            current_table_config.reset(config_token)
            current_fk_whitelist.reset(fk_token)
        if not isinstance(expression, ir.Expr):
            raise Nl2SqlCompileError("execute", "query(config) must return an Ibis expression")
        try:
            return str(to_sql(expression)).strip()
        except Exception as exc:
            raise Nl2SqlCompileError("compile", f"DTE SQL compilation failed: {exc}") from exc


class _IbisQueryAstValidator(ast.NodeVisitor):
    def __init__(self) -> None:
        self._locals: set[str] = {"config"}

    def validate(self, source: str) -> ast.Module:
        if not source.strip():
            raise Nl2SqlCompileError("generation", "Generated Ibis source is empty")
        if len(source) > 24000:
            raise Nl2SqlCompileError("generation", "Generated Ibis source is too long")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise Nl2SqlCompileError("generation", f"Generated Ibis source is invalid Python: {exc}") from exc
        if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
            raise Nl2SqlCompileError("generation", "Generated source must contain exactly one query(config) function")
        function = tree.body[0]
        if function.name != "query" or [arg.arg for arg in function.args.args] != ["config"]:
            raise Nl2SqlCompileError("generation", "Generated function signature must be query(config)")
        if function.decorator_list:
            raise Nl2SqlCompileError("generation", "Generated query function must not use decorators")
        self.visit(tree)
        if not any(isinstance(node, ast.Return) for node in ast.walk(function)):
            raise Nl2SqlCompileError("generation", "Generated query function must return an expression")
        return tree

    def generic_visit(self, node: ast.AST) -> None:
        if isinstance(node, _DISALLOWED_NODES):
            raise Nl2SqlCompileError("generation", f"Python syntax is not allowed: {type(node).__name__}")
        super().generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name != "query":
            raise Nl2SqlCompileError("generation", "Nested functions are not allowed")
        for statement in node.body:
            if not isinstance(statement, (ast.Assign, ast.AnnAssign, ast.Expr, ast.Return, ast.If)):
                raise Nl2SqlCompileError("generation", f"Statement is not allowed: {type(statement).__name__}")
        for statement in node.body:
            self.visit(statement)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if not isinstance(target, ast.Name) or target.id.startswith("_"):
                raise Nl2SqlCompileError("generation", "Assignments must use public local variable names")
            self._locals.add(target.id)
        self.visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if not isinstance(node.target, ast.Name) or node.target.id.startswith("_"):
            raise Nl2SqlCompileError("generation", "Assignments must use public local variable names")
        self._locals.add(node.target.id)
        if node.value is not None:
            self.visit(node.value)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            return
        if node.id in _DISALLOWED_NAMES or node.id.startswith("__"):
            raise Nl2SqlCompileError("generation", f"Name is not allowed: {node.id}")
        if node.id not in self._locals | _SAFE_GLOBALS | {"True", "False", "None", "QueryConfig", "Expr"}:
            raise Nl2SqlCompileError("generation", f"Unknown name: {node.id}")

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("_"):
            raise Nl2SqlCompileError("generation", f"Private attribute is not allowed: {node.attr}")
        self.visit(node.value)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id not in _SAFE_GLOBALS:
            raise Nl2SqlCompileError("generation", f"Direct function call is not allowed: {node.func.id}")
        self.generic_visit(node)


def _build_tables(entities: tuple[dict[str, Any], ...]) -> dict[str, ir.Table]:
    tables: dict[str, ir.Table] = {}
    for entity in entities:
        name = _entity_name(entity)
        if not name or not name.isidentifier():
            continue
        schema = _entity_schema(entity)
        if not schema:
            raise Nl2SqlCompileError("context", f"Logical entity has no usable fields: {name}")
        tables[name] = ibis.table(schema, name=name)
    if not tables:
        raise Nl2SqlCompileError("context", "No logical entity definitions are available")
    return tables


def _entity_name(entity: dict[str, Any]) -> str:
    return str(entity.get("name") or entity.get("logicalEntityName") or entity.get("tableName") or "").strip()


def _entity_schema(entity: dict[str, Any]) -> dict[str, str]:
    raw = entity.get("fields") or entity.get("columns") or entity.get("attributes") or entity.get("schema") or []
    if isinstance(raw, dict):
        return {str(key): _ibis_type(value if isinstance(value, str) else (value or {}).get("type")) for key, value in raw.items()}
    result: dict[str, str] = {}
    if isinstance(raw, list):
        for field in raw:
            if not isinstance(field, dict):
                continue
            key = str(field.get("name") or field.get("field") or field.get("key") or "").strip()
            if key:
                result[key] = _ibis_type(field.get("type") or field.get("dataType") or field.get("fieldType"))
    return result


def _ibis_type(value: object) -> str:
    return _TYPE_ALIASES.get(str(value or "string").strip().lower(), "string")
