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
class QueryResult:
    ret_code: int | str
    ret_info: str
    data: DatasetResult


@dataclass(frozen=True, slots=True)
class Nl2SqlInput:
    question: str


@dataclass(frozen=True, slots=True)
class Nl2SqlOutput:
    sql: str
    intent_function: str


@dataclass(frozen=True, slots=True)
class Sql2DataInput:
    question: str
    sql: str


@dataclass(frozen=True, slots=True)
class Nl2DataOutput:
    sql: str
    intent_function: str
    query_result: QueryResult


@dataclass(frozen=True, slots=True)
class Data2ChartInput:
    question: str
    query_result: QueryResult


@dataclass(frozen=True, slots=True)
class Data2ChartOutput:
    summaries: list[str]
    type: str
    series: list[dict[str, Any]]
    query_result: QueryResult
    title: str = ""
    content: Any | None = None


@dataclass(frozen=True, slots=True)
class Data2SummaryInput:
    question: str
    sql: str
    query_result: QueryResult


@dataclass(frozen=True, slots=True)
class Data2SummaryOutput:
    summaries: list[str]
    title: str = ""
    sql_explanation: str = ""


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
    title: str = ""
    sql_explanation: str = ""


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


def query_result_to_dict(result: QueryResult) -> dict[str, Any]:
    return {
        "retCode": result.ret_code,
        "retInfo": result.ret_info,
        "data": dataset_result_to_dict(result.data),
    }


def query_result_from_dict(payload: object) -> QueryResult:
    value = _object(payload, "query_result")
    if "retCode" not in value:
        raise ValueError("query_result.retCode is required")
    ret_code = value["retCode"]
    if not isinstance(ret_code, (int, str)) or isinstance(ret_code, bool):
        raise ValueError("query_result.retCode must be an integer or string")
    if ret_code not in (0, "0"):
        raise ValueError("query_result must be a successful OneQuery response")
    ret_info = value.get("retInfo")
    if not isinstance(ret_info, str):
        raise ValueError("query_result.retInfo must be a string")
    return QueryResult(ret_code=ret_code, ret_info=ret_info, data=dataset_result_from_dict(value.get("data")))


def nl2sql_input_to_dict(value: Nl2SqlInput) -> dict[str, Any]:
    return {"question": value.question}


def nl2sql_input_from_dict(payload: object) -> Nl2SqlInput:
    return Nl2SqlInput(question=_required_string(_object(payload, "nl2sql input"), "question"))


def nl2sql_output_to_dict(value: Nl2SqlOutput) -> dict[str, Any]:
    return {"sql": value.sql, "intent_function": value.intent_function}


def nl2sql_output_from_dict(payload: object) -> Nl2SqlOutput:
    data = _object(payload, "nl2sql output")
    return Nl2SqlOutput(
        sql=_required_string(data, "sql"),
        intent_function=_required_string(data, "intent_function"),
    )


def sql2data_input_to_dict(value: Sql2DataInput) -> dict[str, Any]:
    return {"question": value.question, "sql": value.sql}


def sql2data_input_from_dict(payload: object) -> Sql2DataInput:
    data = _object(payload, "sql2data input")
    return Sql2DataInput(question=_required_string(data, "question"), sql=_required_string(data, "sql"))


def nl2data_output_to_dict(value: Nl2DataOutput) -> dict[str, Any]:
    return {
        "sql": value.sql,
        "intent_function": value.intent_function,
        "query_result": query_result_to_dict(value.query_result),
    }


def nl2data_output_from_dict(payload: object) -> Nl2DataOutput:
    data = _object(payload, "nl2data output")
    return Nl2DataOutput(
        sql=_required_string(data, "sql"),
        intent_function=_required_string(data, "intent_function"),
        query_result=query_result_from_dict(data.get("query_result")),
    )


def data2chart_input_to_dict(value: Data2ChartInput) -> dict[str, Any]:
    return {"question": value.question, "query_result": query_result_to_dict(value.query_result)}


def data2chart_input_from_dict(payload: object) -> Data2ChartInput:
    data = _object(payload, "data2chart input")
    return Data2ChartInput(
        question=_required_string(data, "question"),
        query_result=query_result_from_dict(data.get("query_result")),
    )


def data2chart_output_to_dict(value: Data2ChartOutput) -> dict[str, Any]:
    return {
        "title": value.title,
        "content": value.content,
        "summaries": list(value.summaries),
        "type": value.type,
        "series": list(value.series),
        "query_result": query_result_to_dict(value.query_result),
    }


def data2chart_output_from_dict(payload: object) -> Data2ChartOutput:
    data = _object(payload, "data2chart output")
    return Data2ChartOutput(
        summaries=_string_list(data.get("summaries"), "summaries"),
        type=_required_string(data, "type"),
        series=_object_list(data.get("series"), "series"),
        query_result=query_result_from_dict(data.get("query_result")),
        title=_optional_string(data.get("title")),
        content=data.get("content"),
    )


def data2summary_input_to_dict(value: Data2SummaryInput) -> dict[str, Any]:
    return {
        "question": value.question,
        "sql": value.sql,
        "query_result": query_result_to_dict(value.query_result),
    }


def data2summary_input_from_dict(payload: object) -> Data2SummaryInput:
    data = _object(payload, "data2summary input")
    return Data2SummaryInput(
        question=_required_string(data, "question"),
        sql=_required_string(data, "sql"),
        query_result=query_result_from_dict(data.get("query_result")),
    )


def data2summary_output_to_dict(value: Data2SummaryOutput) -> dict[str, Any]:
    return {
        "title": value.title,
        "sql_explanation": value.sql_explanation,
        "summaries": list(value.summaries),
    }


def data2summary_output_from_dict(payload: object) -> Data2SummaryOutput:
    data = _object(payload, "data2summary output")
    return Data2SummaryOutput(
        summaries=_string_list(data.get("summaries"), "summaries"),
        title=_optional_string(data.get("title")),
        sql_explanation=_optional_string(data.get("sql_explanation")),
    )


def dataset_result_from_dict(payload: object) -> DatasetResult:
    data = _object(payload, "dataset")
    columns = data.get("columns")
    rows = data.get("results")
    if not isinstance(columns, dict):
        raise ValueError("dataset.columns must be an object")
    if not isinstance(rows, list) or any(not isinstance(item, dict) for item in rows):
        raise ValueError("dataset.results must be an array of objects")
    return DatasetResult(
        columns=[
            DatasetColumn(key=str(key), metadata=dict(value if isinstance(value, dict) else {}))
            for key, value in columns.items()
        ],
        rows=[dict(item) for item in rows],
    )


def data_analysis_answer_to_dict(answer: DataAnalysisAnswer) -> dict[str, Any]:
    payload = {
        "summary": answer.summary,
        "querySpec": query_spec_to_dict(answer.query_spec),
        "sql": answer.query_spec.sql,
        "data": dataset_result_to_dict(answer.data),
        "visualizations": {"components": list(answer.components)},
        "warnings": list(answer.warnings),
    }
    if answer.title:
        payload["title"] = answer.title
    if answer.sql_explanation:
        payload["sqlExplanation"] = answer.sql_explanation
    return payload


def _object(payload: object, name: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must be an object")
    return payload


def _required_string(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _string_list(value: object, name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be an array of strings")
    return list(value)


def _optional_string(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("optional string field must be a string")
    return value.strip()


def _object_list(value: object, name: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError(f"{name} must be an array of objects")
    return [dict(item) for item in value]
