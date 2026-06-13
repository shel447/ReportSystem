"""Small approved helpers exposed to generated Ibis functions."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ....shared.kernel.log import logger


def get_tables_columns(table_exprs: Iterable[Any]) -> dict[str, list[str]]:
    tables: dict[str, list[str]] = {}
    for table in table_exprs:
        try:
            tables[table.get_name()] = list(table.columns)
        except Exception as exc:
            logger.warn("Unable to inspect generated-Ibis table columns: %s", exc)
    return tables
