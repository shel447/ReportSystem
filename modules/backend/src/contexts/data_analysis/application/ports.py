"""External capability ports consumed by data analysis."""

from __future__ import annotations

from typing import Any, Protocol

from ..domain.models import DatasetResult


class OneQueryGateway(Protocol):
    def execute(self, *, query: str, context: dict[str, Any], user_id: str) -> DatasetResult: ...


class ApiDatasetGateway(Protocol):
    def execute(self, *, source: str, payload: dict[str, Any], user_id: str) -> DatasetResult: ...


class DataCatalogGateway(Protocol):
    def list_logical_entities(self, *, user_id: str) -> list[dict[str, Any]]: ...


class KnowledgeGateway(Protocol):
    def retrieve_multi_index(self, *, query: str, user_id: str) -> list[dict[str, Any]]: ...
