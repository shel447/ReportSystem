from __future__ import annotations

import pytest

from src.contexts.data_analysis.application.services import _parse_chart_output, _parse_summary_output
from src.contexts.data_analysis.domain.models import DatasetColumn, DatasetResult, QueryResult
from src.shared.kernel.errors import ErrorCode, ValidationError


def _query_result() -> QueryResult:
    return QueryResult(
        ret_code=0,
        ret_info="",
        data=DatasetResult(
            columns=[
                DatasetColumn("name", {"type": "string"}),
                DatasetColumn("time", {"type": "time"}),
                DatasetColumn("value", {"type": "double"}),
                DatasetColumn("open", {"type": "double"}),
                DatasetColumn("close", {"type": "double"}),
                DatasetColumn("lowest", {"type": "double"}),
                DatasetColumn("highest", {"type": "double"}),
                DatasetColumn("volume", {"type": "double"}),
            ],
            rows=[],
        ),
    )


@pytest.mark.parametrize(
    "chart_type,series,expected_type",
    [
        ("Bar", "name: 指标\n    ex: name\n    ey: value", "bar"),
        ("Line", "name: 指标\n    ex: time\n    ey: value", "line"),
        ("MultiLine", "name: 指标\n    ex: time\n    ey: value", "line"),
        ("Pie", "name: 指标\n    ename: name\n    evalue: value", "pie"),
        ("Ring", "name: 指标\n    ename: name\n    evalue: value", "pie"),
        ("Scatter", "name: 指标\n    ex: value\n    ey: volume", "scatter"),
        ("Radar", "name: 指标\n    ename: name\n    evalue: value", "radar"),
        ("Gauge", "name: 指标\n    ename: name\n    evalue: value", "gauge"),
        (
            "Candlestick",
            "name: 指标\n    time: time\n    open: open\n    close: close\n    lowest: lowest\n    highest: highest\n    volume: volume",
            "candlestick",
        ),
    ],
)
def test_chart_prompt_outputs_map_supported_chart_types(chart_type, series, expected_type):
    output = _parse_chart_output(
        f"title: 测试图表\ntype: {chart_type}\nsummaries: []\nseries:\n  - {series}\n",
        query_result=_query_result(),
    )

    assert output.type == expected_type
    assert output.title == "测试图表"


def test_chart_prompt_rejects_unknown_field_reference():
    with pytest.raises(ValidationError) as exc_info:
        _parse_chart_output(
            "title: 测试\ntype: Bar\nsummaries: []\nseries:\n  - name: 指标\n    ex: missing\n    ey: value\n",
            query_result=_query_result(),
        )

    assert exc_info.value.error_code == ErrorCode.DATA_ANALYSIS_VISUALIZATION_FAILED


def test_chart_prompt_accepts_original_chart_envelope_with_series_type():
    output = _parse_chart_output(
        "title: 设备健康评分\ntype: Chart\nsummaries: []\nseries:\n"
        "  - name: 健康评分\n    type: Bar\n    ex: name\n    ey: value\n",
        query_result=_query_result(),
    )

    assert output.type == "bar"
    assert output.series[0]["type"] == "bar"


def test_summary_prompt_preserves_title_explanation_and_business_summaries():
    output = _parse_summary_output(
        "title: 网络健康\nsql_explanation: 按设备统计健康分。\nsummaries:\n  - 整体稳定。\n"
    )

    assert output.title == "网络健康"
    assert output.sql_explanation == "按设备统计健康分。"
    assert output.summaries == ["整体稳定。"]
