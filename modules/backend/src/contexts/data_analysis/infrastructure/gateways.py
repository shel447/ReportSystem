"""Typed adapters for OneQuery, DataCatalog and Knowledge."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ....infrastructure.platform.cache import MemoryTtlCache, platform_cache
from ....shared.configuration import KnowledgeConfiguration
from ....shared.kernel.errors import ErrorCode, UpstreamError
from ..application.ports import ApiDatasetGateway, DataCatalogGateway, KnowledgeGateway, OneQueryGateway
from ..domain.models import DatasetColumn, DatasetResult, QueryResult


class ExternalOneQueryGateway(OneQueryGateway):
    def __init__(self, *, client) -> None:
        self.client = client

    def execute(self, *, query: str, context: dict[str, Any], user_id: str) -> QueryResult:
        payload = self.client.post_json(
            path_or_url="/rest/dte/v1/onequery/uql/query",
            payload={"query": query, "context": context},
            user_id=user_id,
        )
        if "retCode" not in payload:
            raise UpstreamError(
                "OneQuery response retCode is required",
                error_code=ErrorCode.DATA_ANALYSIS_RESULT_INVALID,
                source="onequery",
                http_status=502,
            )
        if not isinstance(payload.get("retInfo"), str):
            raise UpstreamError(
                "OneQuery response retInfo is required",
                error_code=ErrorCode.DATA_ANALYSIS_RESULT_INVALID,
                source="onequery",
                http_status=502,
            )
        ret_code = payload["retCode"]
        if isinstance(ret_code, bool) or not isinstance(ret_code, (int, str)) or (isinstance(ret_code, str) and not ret_code):
            raise UpstreamError(
                "OneQuery response retCode must be an integer or non-empty string",
                error_code=ErrorCode.DATA_ANALYSIS_RESULT_INVALID,
                source="onequery",
                http_status=502,
            )
        if not _is_success_code(ret_code):
            error_code, message, category, http_status, retryable = _onequery_business_error(
                ret_code=ret_code,
                ret_info=payload["retInfo"],
            )
            raise UpstreamError(
                message,
                details={
                    "retCode": ret_code,
                    "upstreamCode": str(ret_code),
                    "retInfo": payload["retInfo"],
                    "sql": query,
                },
                error_code=error_code,
                category=category,
                retryable=retryable,
                source="onequery",
                http_status=http_status,
            )
        data = payload.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("columns"), dict) or not isinstance(data.get("results"), list):
            raise UpstreamError(
                "OneQuery response data.columns/data.results is required",
                error_code=ErrorCode.DATA_ANALYSIS_RESULT_INVALID,
                source="onequery",
                http_status=502,
            )
        return QueryResult(
            ret_code=ret_code,
            ret_info=payload["retInfo"],
            data=DatasetResult(
                columns=[DatasetColumn(key=str(key), metadata=deepcopy(metadata if isinstance(metadata, dict) else {})) for key, metadata in data["columns"].items()],
                rows=deepcopy(data["results"]),
            ),
        )


class ExternalApiDatasetGateway(ApiDatasetGateway):
    def __init__(self, *, client) -> None:
        self.client = client

    def execute(self, *, source: str, payload: dict[str, Any], user_id: str) -> DatasetResult:
        response = self.client.post_json(path_or_url=source, payload=payload, user_id=user_id)
        if "retCode" not in response:
            raise UpstreamError(
                "API dataset response retCode is required",
                error_code=ErrorCode.DATA_ANALYSIS_RESULT_INVALID,
                source="api_dataset",
                http_status=502,
            )
        ret_code = int(response["retCode"])
        if ret_code != 0:
            raise UpstreamError(
                str(response.get("retInfo") or f"API dataset failed: {ret_code}"),
                details={"retCode": ret_code},
                error_code=ErrorCode.DATA_ANALYSIS_DATASOURCE_UNAVAILABLE,
                source="api_dataset",
                http_status=502,
            )
        data = response.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("columns"), dict) or not isinstance(data.get("results"), list):
            raise UpstreamError(
                "API dataset response data.columns/data.results is required",
                error_code=ErrorCode.DATA_ANALYSIS_RESULT_INVALID,
                source="api_dataset",
                http_status=502,
            )
        return DatasetResult(
            columns=[DatasetColumn(key=str(key), metadata=deepcopy(metadata if isinstance(metadata, dict) else {})) for key, metadata in data["columns"].items()],
            rows=deepcopy(data["results"]),
        )


class ExternalDataCatalogGateway(DataCatalogGateway):
    def __init__(self, *, client, cache: MemoryTtlCache | None = None) -> None:
        self.client = client
        self.cache = cache or platform_cache

    def list_logical_entities(self, *, user_id: str) -> list[dict[str, Any]]:
        key = f"datacatalog:{user_id}:logical_entities"
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
            key=f"datacatalog:{user_id}:logical_entity:{name}",
            path="/rest/odae/v3/datacatalog/model/logicalentity",
            params={"logicalEntityName": name},
            user_id=user_id,
        )

    def get_dataset(self, *, name: str, user_id: str) -> dict[str, Any]:
        return self._cached_get(
            key=f"datacatalog:{user_id}:dataset:{name}",
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
        key = f"datacatalog:{user_id}:logical_relation:{name}"
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
        _ensure_success(payload, service="DataCatalog")
        result = deepcopy(dict(payload.get("data") or {}))
        self.cache.set(key, result, ttl_seconds=600)
        return result


class ExternalKnowledgeGateway(KnowledgeGateway):
    def __init__(
        self,
        *,
        client,
        configuration: KnowledgeConfiguration | None = None,
        cache: MemoryTtlCache | None = None,
    ) -> None:
        self.client = client
        self.configuration = configuration or KnowledgeConfiguration()
        self.cache = cache or platform_cache

    def retrieve_multi_index(self, *, query: str, user_id: str) -> list[dict[str, Any]]:
        key = f"rag:{user_id}:retriever:{self.configuration.nl2sql_index_name}:{query}"
        cached = self.cache.get(key)
        if cached is not None:
            return deepcopy(cached)
        payload = self.client.post_json(
            path_or_url="/rest/naie/rag/v1/retriever",
            payload={
                "query": query,
                "rankTopN": self.configuration.rank_top_n,
                "ragIndexes": [
                    {
                        "ragIndex": self.configuration.nl2sql_index_name,
                        "indexType": "NL2SQL",
                        "esTopN": self.configuration.es_top_n,
                        "vsTopN": self.configuration.vs_top_n,
                        "filters": {},
                    }
                ],
                "ranking_options": {
                    "ranker": "DEFAULT",
                    "score_threshold": self.configuration.score_threshold,
                },
                "enableHybridResults": self.configuration.enable_hybrid_results,
            },
            user_id=user_id,
        )
        result = list(payload.get("recommends") or [])
        self.cache.set(key, deepcopy(result), ttl_seconds=300)
        return result

    def retrieve_sql_few_shot(self, *, query: str, user_id: str) -> list[dict[str, Any]]:
        index_name = self.configuration.index.chatbi_sql_few_shot
        if not index_name:
            return []
        return self.retrieve_knowledge(query=query, rag_index=index_name, user_id=user_id)

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
        raise UpstreamError(
            f"{service} failed: {payload.get('retInfo') or ''}",
            error_code=ErrorCode.DATA_ANALYSIS_DATASOURCE_UNAVAILABLE,
            source=service.lower(),
            http_status=502,
        )


def _is_success_code(value: object) -> bool:
    return not isinstance(value, bool) and (value == 0 or value == "0")


def _onequery_business_error(*, ret_code: object, ret_info: str) -> tuple[str, str, str, int, bool]:
    code = str(ret_code)
    if code == "04003":
        return (
            ErrorCode.DATA_ANALYSIS_QUERY_UNSUPPORTED_SYNTAX,
            "查询使用了当前数据源不支持的 CONNECT BY 语法。",
            "query",
            422,
            False,
        )
    if code == "04023":
        return (
            ErrorCode.DATA_ANALYSIS_QUERY_FIELD_NOT_FOUND,
            "查询引用的字段不存在。",
            "query",
            422,
            False,
        )
    return (
        ErrorCode.DATA_ANALYSIS_DATASOURCE_UNAVAILABLE,
        ret_info or f"OneQuery failed: {code}",
        "upstream",
        502,
        True,
    )
