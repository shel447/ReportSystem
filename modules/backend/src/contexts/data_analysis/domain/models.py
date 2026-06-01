"""Pure data-analysis domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DatasetColumn:
    key: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DatasetResult:
    columns: list[DatasetColumn] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class QuerySpec:
    intent: str
    sql: str
    entities: list[str] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    measures: list[str] = field(default_factory=list)
    filters: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class DataAnalysisAnswer:
    summary: str
    query_spec: QuerySpec
    data: DatasetResult
    components: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)


def query_spec_to_dict(spec: QuerySpec) -> dict[str, Any]:
    return {
        "intent": spec.intent,
        "sql": spec.sql,
        "entities": list(spec.entities),
        "dimensions": list(spec.dimensions),
        "measures": list(spec.measures),
        "filters": list(spec.filters),
    }


def dataset_result_to_dict(result: DatasetResult) -> dict[str, Any]:
    return {
        "columns": {item.key: dict(item.metadata) for item in result.columns},
        "results": list(result.rows),
    }


def data_analysis_answer_to_dict(answer: DataAnalysisAnswer) -> dict[str, Any]:
    return {
        "summary": answer.summary,
        "querySpec": query_spec_to_dict(answer.query_spec),
        "sql": answer.query_spec.sql,
        "data": dataset_result_to_dict(answer.data),
        "visualizations": {"components": list(answer.components)},
        "warnings": list(answer.warnings),
    }
