"""Infrastructure data structures used while compiling generated Ibis code."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ForeignKey:
    stmt: str = ""
    table: str = ""
    column: str = ""
    ref_table: str = ""
    ref_column: str = ""

    def __str__(self) -> str:
        return self.stmt or f"{self.table}.{self.column} = {self.ref_table}.{self.ref_column}"

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "ForeignKey":
        source = value.get("source") if isinstance(value.get("source"), dict) else {}
        target = value.get("target") if isinstance(value.get("target"), dict) else {}
        return cls(
            stmt=str(value.get("stmt") or value.get("expression") or ""),
            table=_text(value, "table", "sourceTable", "sourceEntity") or _text(source, "table", "entity", "name"),
            column=_text(value, "column", "sourceColumn", "sourceField") or _text(source, "column", "field"),
            ref_table=_text(value, "refTable", "targetTable", "targetEntity") or _text(target, "table", "entity", "name"),
            ref_column=_text(value, "refColumn", "targetColumn", "targetField") or _text(target, "column", "field"),
        )

    @property
    def complete(self) -> bool:
        return all((self.table, self.column, self.ref_table, self.ref_column))


def _text(value: dict[str, Any], *keys: str) -> str:
    for key in keys:
        candidate = value.get(key)
        if candidate is not None and str(candidate).strip():
            return str(candidate).strip()
    return ""
