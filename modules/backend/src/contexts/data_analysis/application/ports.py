"""External capability ports consumed by data analysis."""

from __future__ import annotations

from typing import Any, Protocol

from ..domain.models import DatasetResult, Nl2SqlContext, QueryResult


class OneQueryGateway(Protocol):
    def execute(self, *, query: str, context: dict[str, Any], user_id: str) -> QueryResult: ...


class ApiDatasetGateway(Protocol):
    def execute(self, *, source: str, payload: dict[str, Any], user_id: str) -> DatasetResult: ...


class DataCatalogGateway(Protocol):
    def list_logical_entities(self, *, user_id: str) -> list[dict[str, Any]]: ...
    def get_logical_entity(self, *, name: str, user_id: str) -> dict[str, Any]: ...
    def list_logical_relations(self, *, user_id: str) -> list[dict[str, Any]]: ...


class KnowledgeGateway(Protocol):
    def retrieve_multi_index(self, *, query: str, user_id: str) -> list[dict[str, Any]]: ...
    def retrieve_sql_few_shot(self, *, query: str, user_id: str) -> list[dict[str, Any]]: ...


class Nl2SqlCompiler(Protocol):
    def compile(self, *, source: str, context: Nl2SqlContext) -> str: ...
