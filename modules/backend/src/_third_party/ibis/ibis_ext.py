import re

import ibis.expr.types as ir
import sqlglot.errors
from ibis.expr.sql import SQLString
from sqlglot.optimizer import optimize, RULES

from .backends.sql.compilers.compiler import DTESQLCompiler

from .backends.sql.sqlglot.custom_optimize_rules import (
    rename_count_alias,
    make_up_connect_by,
)
from .state import CompileSqlState, compile_sql_state

from sqlglot.optimizer.canonicalize import canonicalize
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.pushdown_projections import pushdown_projections
from sqlglot.optimizer.normalize import normalize
from sqlglot.optimizer.pushdown_predicates import pushdown_predicates
from sqlglot.optimizer.optimize_joins import optimize_joins
from sqlglot.optimizer.merge_subqueries import merge_subqueries
from sqlglot.optimizer.eliminate_joins import eliminate_joins
from sqlglot.optimizer.annotate_types import annotate_types
from sqlglot.optimizer.qualify_columns import quote_identifiers


_compiler = DTESQLCompiler()


def to_sql(expr: ir.Expr, pretty: bool = True, **kwargs) -> SQLString:
    token = compile_sql_state.set(CompileSqlState())
    try:
        out = _compiler.to_sqlglot(expr, **kwargs)
        queries = out if isinstance(out, list) else [out]
        dialect = _compiler.dialect
        sql = ";\n".join(query.sql(dialect=dialect, pretty=pretty) for query in queries)
        optimize_rules = custom_optimize_rules(sql)
        sql = optimize_sql(sql, optimize_rules, dialect, pretty)
        return SQLString(sql)
    finally:
        compile_sql_state.reset(token)


def optimize_sql(sql: str, rules: list, dialect, pretty):
    try:
        sql = optimize(sql, rules=rules).sql(dialect=dialect, pretty=pretty)
    except sqlglot.errors.OptimizeError as e:
        raise custom_error_message(e) from e

    return SQLString(sql)


def custom_error_message(error):
    handle_unresolved_table(error)
    return error


def handle_unresolved_table(error):
    message = error.args[0]
    pattern = r"could not be resolved for table: '(\w+)'"
    match = re.search(pattern, message)
    if match:
        raise sqlglot.errors.OptimizeError(
            f"The {match.group(1)} tables were not explicitly joined or materialized, "
            "leading to references without inclusion in SQL clauses."
        )


def custom_optimize_rules(sql: str):
    # 递归标记
    if 'WITH "__connect"' in sql:
        return [
            make_up_connect_by,
            qualify,
            pushdown_projections,
            normalize,
            pushdown_predicates,
            optimize_joins,
            merge_subqueries,
            eliminate_joins,
            quote_identifiers,
            annotate_types,
            canonicalize,
            rename_count_alias,
        ]
    else:
        return [*RULES] + [rename_count_alias]
