from __future__ import annotations

import pytest

from src.contexts.data_analysis.domain.models import (
    Data2ChartInput,
    Data2ChartOutput,
    Data2SummaryInput,
    Data2SummaryOutput,
    DatasetColumn,
    DatasetResult,
    Nl2DataOutput,
    Nl2SqlInput,
    Nl2SqlOutput,
    QueryResult,
    Sql2DataInput,
    data2chart_input_from_dict,
    data2chart_input_to_dict,
    data2chart_output_from_dict,
    data2chart_output_to_dict,
    data2summary_input_from_dict,
    data2summary_input_to_dict,
    data2summary_output_from_dict,
    data2summary_output_to_dict,
    nl2data_output_from_dict,
    nl2data_output_to_dict,
    nl2sql_input_from_dict,
    nl2sql_input_to_dict,
    nl2sql_output_from_dict,
    nl2sql_output_to_dict,
    query_result_from_dict,
    query_result_to_dict,
    sql2data_input_from_dict,
    sql2data_input_to_dict,
)
from src.shared.kernel.errors import ValidationError


def _query_result() -> QueryResult:
    return QueryResult(
        ret_code=0,
        ret_info="",
        data=DatasetResult(
            columns=[DatasetColumn(key="health_score", metadata={"type": "double"})],
            rows=[{"health_score": 98.5}],
        ),
    )


def test_data_analysis_step_contracts_round_trip():
    query_result = _query_result()
    values = [
        (Nl2SqlInput("查询核心设备健康评分"), nl2sql_input_to_dict, nl2sql_input_from_dict),
        (
            Nl2SqlOutput("select health_score"),
            nl2sql_output_to_dict,
            nl2sql_output_from_dict,
        ),
        (Sql2DataInput("查询核心设备健康评分", "select health_score"), sql2data_input_to_dict, sql2data_input_from_dict),
        (
            Nl2DataOutput("select health_score", query_result),
            nl2data_output_to_dict,
            nl2data_output_from_dict,
        ),
        (Data2ChartInput("查询核心设备健康评分", query_result), data2chart_input_to_dict, data2chart_input_from_dict),
        (
            Data2ChartOutput(
                [],
                "bar",
                [{"type": "bar", "ex": "device_name", "ey": "health_score"}],
                query_result,
                title="健康评分",
            ),
            data2chart_output_to_dict,
            data2chart_output_from_dict,
        ),
        (
            Data2SummaryInput("查询核心设备健康评分", "select health_score", query_result),
            data2summary_input_to_dict,
            data2summary_input_from_dict,
        ),
        (
            Data2SummaryOutput(
                ["核心设备整体稳定。"],
                title="健康评分",
                sql_explanation="按设备展示健康评分。",
            ),
            data2summary_output_to_dict,
            data2summary_output_from_dict,
        ),
        (query_result, query_result_to_dict, query_result_from_dict),
    ]

    for value, serialize, deserialize in values:
        assert deserialize(serialize(value)) == value


@pytest.mark.parametrize(
    "deserialize,payload",
    [
        (nl2sql_input_from_dict, {}),
        (nl2sql_output_from_dict, {}),
        (sql2data_input_from_dict, {"question": "test"}),
        (query_result_from_dict, {"retCode": 0, "retInfo": ""}),
        (data2chart_input_from_dict, {"question": "test"}),
        (data2summary_input_from_dict, {"question": "test", "sql": "select 1"}),
    ],
)
def test_data_analysis_step_contracts_reject_missing_fields(deserialize, payload):
    with pytest.raises(ValueError):
        deserialize(payload)
