from __future__ import annotations

import pytest

from src.contexts.data_analysis.infrastructure.gateways import (
    ExternalApiDatasetGateway,
    ExternalDataCatalogGateway,
    ExternalKnowledgeGateway,
    ExternalOneQueryGateway,
)
from src.infrastructure.platform.cache import MemoryTtlCache
from src.shared.kernel.errors import UpstreamError


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
    assert result.columns[0].metadata["lineageTracing"]["sources"][0]["field"] == "score"
    assert result.rows == [{"health_score": 98.5}]


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


def test_rag_cache_is_isolated_by_user_id():
    client = _Client({"recommends": [{"query": "select 1"}]})
    gateway = ExternalKnowledgeGateway(client=client, cache=MemoryTtlCache())

    assert gateway.retrieve_multi_index(query="设备健康", user_id="user-a") == [{"query": "select 1"}]
    assert gateway.retrieve_multi_index(query="设备健康", user_id="user-a") == [{"query": "select 1"}]
    assert gateway.retrieve_multi_index(query="设备健康", user_id="user-b") == [{"query": "select 1"}]

    assert [call["user_id"] for call in client.calls] == ["user-a", "user-b"]
