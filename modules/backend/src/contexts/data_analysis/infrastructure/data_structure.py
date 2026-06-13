"""Infrastructure data structures used while compiling generated Ibis code."""

from __future__ import annotations

from dataclasses import dataclass
import re
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
        relationship = _relationship_fields(value)
        if relationship is not None:
            return cls(
                stmt=str((value.get("rule") or {}).get("condition") or ""),
                table=relationship[0],
                column=relationship[1],
                ref_table=relationship[2],
                ref_column=relationship[3],
            )
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


_SIMPLE_EQUALITY = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"
    r"([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\s*$"
)


def _relationship_fields(value: dict[str, Any]) -> tuple[str, str, str, str] | None:
    rule = value.get("rule")
    if not isinstance(rule, dict) or rule.get("conditionType") != "sql":
        return None
    match = _SIMPLE_EQUALITY.fullmatch(str(rule.get("condition") or ""))
    if match is None:
        return None
    left_entity, left_field, right_entity, right_field = match.groups()
    source = str(value.get("sourceEntityName") or "")
    target = str(value.get("targetEntityName") or "")
    if (left_entity, right_entity) == (source, target):
        return left_entity, left_field, right_entity, right_field
    if (left_entity, right_entity) == (target, source):
        return right_entity, right_field, left_entity, left_field
    return None
