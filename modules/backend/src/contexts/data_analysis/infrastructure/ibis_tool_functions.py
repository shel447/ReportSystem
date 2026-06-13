"""Approved higher-level Ibis helpers available to generated query functions."""

from __future__ import annotations

from collections import deque

import ibis.expr.types as ir

from ...._third_party.ibis.backends.sql.sqlglot.custom_optimize_rules import ConnectBySchema
from ..domain.models import Nl2SqlCompileError
from .contextvar import current_fk_whitelist


def create_recursive_query(
    root_table_expr: ir.Table,
    id_col: str,
    parent_col: str,
    start_condition: ir.Expr | None = None,
    max_depth: int = 2,
    include_columns: list[str] | None = None,
    include_root_layer: bool = False,
) -> ir.Expr:
    del max_depth
    table = root_table_expr.mutate(__connect_by_info_field=f"{id_col}")
    columns = list(dict.fromkeys([id_col, parent_col, *(include_columns or [])]))
    condition = start_condition if start_condition is not None else table[parent_col].isnull()
    marker = ConnectBySchema(
        level=0 if include_root_layer else 1,
        prior_column=id_col,
        no_prior_column=parent_col,
    ).format()
    return table.filter(condition & (table.__connect_by_info_field == marker)).select(columns).alias("__connect").as_table()


def create_device2kpi_wide_table(
    device_table: ir.Table,
    kpi_metrics_table: ir.Table,
    intermediate_tables: list[ir.Table],
) -> ir.Table:
    """Join an approved device-to-KPI relation path into one Ibis table."""

    available = {table.get_name(): table for table in [device_table, *intermediate_tables, kpi_metrics_table]}
    start = device_table.get_name()
    target = kpi_metrics_table.get_name()
    result = device_table
    current = start
    for relation, next_table in _relation_path(start=start, target=target, available=set(available)):
        right = available[next_table]
        predicate = (
            result[relation.column] == right[relation.ref_column]
            if relation.table == current
            else result[relation.ref_column] == right[relation.column]
        )
        result = result.join(right, predicate)
        current = next_table
    return result


def _relation_path(*, start: str, target: str, available: set[str]):
    if start == target:
        raise Nl2SqlCompileError("execute", "Device table and KPI table must be different")
    relations = tuple(item for item in current_fk_whitelist.get() if item.complete)
    queue = deque([(start, [])])
    visited = {start}
    while queue:
        current, path = queue.popleft()
        for relation in relations:
            next_table = relation.ref_table if relation.table == current else relation.table if relation.ref_table == current else ""
            if not next_table or next_table not in available or next_table in visited:
                continue
            next_path = [*path, (relation, next_table)]
            if next_table == target:
                return next_path
            visited.add(next_table)
            queue.append((next_table, next_path))
    raise Nl2SqlCompileError("execute", f"No approved relation path from {start} to {target}")
