"""Typed adapters for OneQuery, DataCatalog and Knowledge."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ....infrastructure.platform.cache import MemoryTtlCache, platform_cache
from ....shared.kernel.errors import UpstreamError
from ..domain.models import DatasetColumn, DatasetResult


class ExternalOneQueryGateway:
    def __init__(self, *, client) -> None:
        self.client = client

    def execute(self, *, query: str, context: dict[str, Any], user_id: str) -> DatasetResult:
        payload = self.client.post_json(
            path_or_url="/rest/dte/v1/onequery/uql/query",
            payload={"query": query, "context": context},
            user_id=user_id,
        )
        if "retCode" not in payload:
            raise UpstreamError("OneQuery response retCode is required")
        ret_code = int(payload["retCode"])
        if ret_code != 0:
            raise UpstreamError(str(payload.get("retInfo") or f"OneQuery failed: {ret_code}"), details={"retCode": ret_code})
        data = payload.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("columns"), dict) or not isinstance(data.get("results"), list):
            raise UpstreamError("OneQuery response data.columns/data.results is required")
        return DatasetResult(
            columns=[DatasetColumn(key=str(key), metadata=deepcopy(metadata if isinstance(metadata, dict) else {})) for key, metadata in data["columns"].items()],
            rows=deepcopy(data["results"]),
        )


class ExternalApiDatasetGateway:
    def __init__(self, *, client) -> None:
        self.client = client

    def execute(self, *, source: str, payload: dict[str, Any], user_id: str) -> DatasetResult:
        response = self.client.post_json(path_or_url=source, payload=payload, user_id=user_id)
        if "retCode" not in response:
            raise UpstreamError("API dataset response retCode is required")
        ret_code = int(response["retCode"])
        if ret_code != 0:
            raise UpstreamError(str(response.get("retInfo") or f"API dataset failed: {ret_code}"), details={"retCode": ret_code})
        data = response.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("columns"), dict) or not isinstance(data.get("results"), list):
            raise UpstreamError("API dataset response data.columns/data.results is required")
        return DatasetResult(
            columns=[DatasetColumn(key=str(key), metadata=deepcopy(metadata if isinstance(metadata, dict) else {})) for key, metadata in data["columns"].items()],
            rows=deepcopy(data["results"]),
        )


class ExternalDataCatalogGateway:
    def __init__(self, *, client, cache: MemoryTtlCache | None = None) -> None:
        self.client = client
        self.cache = cache or platform_cache

    def list_logical_entities(self, *, user_id: str) -> list[dict[str, Any]]:
        key = "datacatalog:logical_entities"
        cached = self.cache.get(key)
        if cached is not None:
            return deepcopy(cached)
        payload = self.client.post_json(
            path_or_url="/rest/odae/v3/datacatalog/model/logicalentities/list",
            payload={"pageSize": 100, "pageNo": 1, "filter": {"includeSchemaOfParent": True}},
            user_id=user_id,
        )
        _ensure_success(payload, service="DataCatalog")
        result = list((payload.get("data") or {}).get("results") or [])
        self.cache.set(key, deepcopy(result), ttl_seconds=600)
        return result

    def get_logical_entity(self, *, name: str, user_id: str) -> dict[str, Any]:
        return self._cached_get(
            key=f"datacatalog:logical_entity:{name}",
            path="/rest/odae/v3/datacatalog/model/logicalentity",
            params={"logicalEntityName": name},
            user_id=user_id,
        )

    def get_dataset(self, *, name: str, user_id: str) -> dict[str, Any]:
        return self._cached_get(
            key=f"datacatalog:dataset:{name}",
            path=f"/rest/odae/v3/datacatalog/model/datasets/{name}",
            params=None,
            user_id=user_id,
        )

    def list_logical_relations(self, *, user_id: str) -> list[dict[str, Any]]:
        payload = self.client.post_json(
            path_or_url="/rest/dte/v2/datacatalog/product/model/logicalrelations/query",
            payload={"pageSize": 100, "pageNo": 1, "filter": {}},
            user_id=user_id,
        )
        _ensure_success(payload, service="DataCatalog")
        return list((payload.get("data") or {}).get("results") or [])

    def get_logical_relation(self, *, name: str, user_id: str) -> dict[str, Any]:
        key = f"datacatalog:logical_relation:{name}"
        cached = self.cache.get(key)
        if cached is not None:
            return deepcopy(cached)
        payload = self.client.get_json(
            path_or_url="/rest/dte/v2/datacatalog/product/model/logicalrelation",
            params={"name": name},
            user_id=user_id,
        )
        _ensure_success(payload, service="DataCatalog")
        result = deepcopy(dict(payload.get("data") or {}))
        self.cache.set(key, result, ttl_seconds=600)
        return result

    def _cached_get(self, *, key: str, path: str, params: dict[str, Any] | None, user_id: str) -> dict[str, Any]:
        cached = self.cache.get(key)
        if cached is not None:
            return deepcopy(cached)
        payload = self.client.get_json(path_or_url=path, params=params, user_id=user_id)
        result = deepcopy(dict(payload.get("data") or {}))
        self.cache.set(key, result, ttl_seconds=600)
        return result


class ExternalKnowledgeGateway:
    def __init__(self, *, client, cache: MemoryTtlCache | None = None) -> None:
        self.client = client
        self.cache = cache or platform_cache

    def retrieve_multi_index(self, *, query: str, user_id: str) -> list[dict[str, Any]]:
        key = f"rag:retriever:{query}"
        cached = self.cache.get(key)
        if cached is not None:
            return deepcopy(cached)
        payload = self.client.post_json(
            path_or_url="/rest/naie/rag/v1/retriever",
            payload={
                "query": query,
                "rankTopN": 3,
                "ragIndexes": [{"ragIndex": "nl2sql_cache", "indexType": "NL2SQL", "esTopN": 5, "vsTopN": 5, "filters": {}}],
                "ranking_options": {"ranker": "DEFAULT", "score_threshold": 0.5},
                "enableHybridResults": True,
            },
            user_id=user_id,
        )
        result = list(payload.get("recommends") or [])
        self.cache.set(key, deepcopy(result), ttl_seconds=300)
        return result

    def query_knowledge(self, *, user_id: str, **filters: Any) -> list[dict[str, Any]]:
        payload = self.client.get_json(path_or_url="/rest/naie/knwl/v1/knowledge", params=filters, user_id=user_id)
        return list(payload.get("knowledgeList") or [])

    def retrieve_knowledge(self, *, query: str, rag_index: str, user_id: str) -> list[dict[str, Any]]:
        payload = self.client.post_json(
            path_or_url="/rest/naie/rag/v1/retriever-klg",
            payload={"query": query, "ragIndex": rag_index, "extensions": [], "esTopN": 5, "vsTopN": 5, "rankTopN": 3},
            user_id=user_id,
        )
        return list(payload.get("recommends") or [])


def _ensure_success(payload: dict[str, Any], *, service: str) -> None:
    if int(payload.get("retCode") or 0) != 0:
        raise UpstreamError(f"{service} failed: {payload.get('retInfo') or ''}")
