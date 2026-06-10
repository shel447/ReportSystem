from __future__ import annotations

import pytest

from src.contexts.data_analysis.infrastructure.gateways import (
    ExternalApiDatasetGateway,
    ExternalDataCatalogGateway,
    ExternalKnowledgeGateway,
    ExternalOneQueryGateway,
)
from src.infrastructure.platform.cache import MemoryTtlCache
from src.shared.agentflow.metrics import FlowMetricsCollector, use_metrics_collector
from src.shared.kernel.errors import ErrorCode, UpstreamError


class _Client:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def post_json(self, **kwargs):
        self.calls.append(kwargs)
        return self.payload


def test_onequery_uses_formal_path_and_preserves_column_metadata():
    client = _Client(
        {
            "retCode": 0,
            "retInfo": "",
            "data": {
                "columns": {"health_score": {"type": "double", "lineageTracing": {"sources": [{"field": "score"}]}}},
                "results": [{"health_score": 98.5}],
            },
        }
    )

    result = ExternalOneQueryGateway(client=client).execute(query="select health_score", context={}, user_id="default")

    assert client.calls[0]["path_or_url"] == "/rest/dte/v1/onequery/uql/query"
    assert result.ret_code == 0
    assert result.data.columns[0].metadata["lineageTracing"]["sources"][0]["field"] == "score"
    assert result.data.rows == [{"health_score": 98.5}]


@pytest.mark.parametrize(
    ("ret_code", "ret_info", "error_code", "message"),
    [
        ("04003", "dblink does not support connect by", ErrorCode.DATA_ANALYSIS_QUERY_UNSUPPORTED_SYNTAX, "CONNECT BY"),
        ("04023", "query field does not exist", ErrorCode.DATA_ANALYSIS_QUERY_FIELD_NOT_FOUND, "字段不存在"),
    ],
)
def test_onequery_maps_known_string_business_errors_without_losing_leading_zero(ret_code, ret_info, error_code, message):
    gateway = ExternalOneQueryGateway(client=_Client({"retCode": ret_code, "retInfo": ret_info}))

    with pytest.raises(UpstreamError, match=message) as captured:
        gateway.execute(query="select missing_field from network_health", context={}, user_id="default")

    error = captured.value
    assert error.error_code == error_code
    assert error.retryable is False
    assert error.details == {
        "retCode": ret_code,
        "upstreamCode": ret_code,
        "retInfo": ret_info,
        "sql": "select missing_field from network_health",
    }


def test_onequery_accepts_string_zero_success_code():
    result = ExternalOneQueryGateway(
        client=_Client({"retCode": "0", "retInfo": "", "data": {"columns": {}, "results": []}})
    ).execute(query="select 1", context={}, user_id="default")

    assert result.ret_code == "0"


def test_onequery_unknown_business_error_keeps_existing_retryable_datasource_semantics():
    gateway = ExternalOneQueryGateway(client=_Client({"retCode": 1001, "retInfo": "temporary query failure"}))

    with pytest.raises(UpstreamError) as captured:
        gateway.execute(query="select 1", context={}, user_id="default")

    assert captured.value.error_code == ErrorCode.DATA_ANALYSIS_DATASOURCE_UNAVAILABLE
    assert captured.value.category == "upstream"
    assert captured.value.retryable is True


def test_onequery_rejects_response_without_ret_info():
    gateway = ExternalOneQueryGateway(client=_Client({"retCode": 0, "data": {"columns": {}, "results": []}}))

    with pytest.raises(UpstreamError, match="retInfo is required"):
        gateway.execute(query="select 1", context={}, user_id="default")


@pytest.mark.parametrize("gateway", [ExternalOneQueryGateway, ExternalApiDatasetGateway])
def test_dataset_gateway_rejects_response_without_ret_code(gateway):
    client = _Client({"data": {"columns": {}, "results": []}})

    with pytest.raises(UpstreamError, match="retCode is required"):
        if gateway is ExternalOneQueryGateway:
            gateway(client=client).execute(query="select 1", context={}, user_id="default")
        else:
            gateway(client=client).execute(source="/rest/datasets/network_health", payload={}, user_id="default")


def test_datacatalog_cache_is_isolated_by_user_id():
    client = _Client({"retCode": 0, "data": {"results": [{"name": "device"}]}})
    gateway = ExternalDataCatalogGateway(client=client, cache=MemoryTtlCache())

    assert gateway.list_logical_entities(user_id="user-a") == [{"name": "device"}]
    assert gateway.list_logical_entities(user_id="user-a") == [{"name": "device"}]
    assert gateway.list_logical_entities(user_id="user-b") == [{"name": "device"}]

    assert [call["user_id"] for call in client.calls] == ["user-a", "user-b"]


def test_datacatalog_records_logical_entity_metrics_when_flow_collector_exists():
    client = _Client({"retCode": 0, "data": {"results": [{"name": "device"}, {"logicalEntityName": "interface"}, {"name": "device"}]}})
    gateway = ExternalDataCatalogGateway(client=client, cache=MemoryTtlCache())
    collector = FlowMetricsCollector()

    with use_metrics_collector(collector):
        gateway.list_logical_entities(user_id="user-a")

    metrics = collector.snapshot(run_id="run_1", status="finished")
    assert metrics.unique_counts["datacatalog.logical_entity.used"] == 2


def test_rag_cache_is_isolated_by_user_id():
    client = _Client({"recommends": [{"query": "select 1"}]})
    gateway = ExternalKnowledgeGateway(client=client, cache=MemoryTtlCache())

    assert gateway.retrieve_multi_index(query="设备健康", user_id="user-a") == [{"query": "select 1"}]
    assert gateway.retrieve_multi_index(query="设备健康", user_id="user-a") == [{"query": "select 1"}]
    assert gateway.retrieve_multi_index(query="设备健康", user_id="user-b") == [{"query": "select 1"}]

    assert [call["user_id"] for call in client.calls] == ["user-a", "user-b"]
