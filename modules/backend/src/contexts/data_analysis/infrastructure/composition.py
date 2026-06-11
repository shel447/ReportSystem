"""Composition builder for the data-analysis context."""

from __future__ import annotations

from ....infrastructure.ai.openai_compat import OpenAICompatGateway
from ....infrastructure.platform.guardrail import ExternalGuardrailGateway
from ....infrastructure.platform.http_client import PlatformHttpClient
from ....infrastructure.platform.runtime import audit_publisher, build_platform_client
from ....infrastructure.settings.system_settings import build_completion_provider_config
from ..application.services import DataAnalysisService, DataQueryService
from .gateways import (
    ExternalApiDatasetGateway,
    ExternalDataCatalogGateway,
    ExternalKnowledgeGateway,
    ExternalOneQueryGateway,
)
from .scenario_registration import DataAnalysisScenarioRegistrationProvider


def _client(*, service_key: str | None = None) -> PlatformHttpClient:
    return build_platform_client(service_key=service_key)


def build_data_query_gateway() -> DataQueryService:
    client = _client(service_key="query")
    return DataQueryService(
        onequery_gateway=ExternalOneQueryGateway(client=client),
        api_gateway=ExternalApiDatasetGateway(client=client),
    )


def build_data_analysis_service() -> DataAnalysisService:
    client = _client(service_key="analysis")
    return DataAnalysisService(
        query_service=build_data_query_gateway(),
        data_catalog_gateway=ExternalDataCatalogGateway(client=client),
        knowledge_gateway=ExternalKnowledgeGateway(client=client),
        guardrail_gateway=ExternalGuardrailGateway(client=_client(service_key="guardrail")),
        ai_gateway=OpenAICompatGateway(),
        completion_config_builder=build_completion_provider_config,
        audit_publisher=audit_publisher,
    )


def build_data_analysis_scenario_provider(service: DataAnalysisService | None = None) -> DataAnalysisScenarioRegistrationProvider:
    return DataAnalysisScenarioRegistrationProvider(service=service or build_data_analysis_service())
