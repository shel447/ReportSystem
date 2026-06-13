"""Composition builder for the data-analysis context."""

from __future__ import annotations

from ....infrastructure.ai.openai_compat import OpenAICompatGateway
from ....infrastructure.configuration import (
    build_completion_provider_config,
    get_knowledge_configuration,
)
from ....infrastructure.platform.guardrail import ExternalGuardrailGateway
from ....infrastructure.platform.client import RuntimeHttpClient
from ....infrastructure.platform.runtime import audit_publisher, build_runtime_client
from ....infrastructure.prompts import get_prompt_catalog
from ..application.services import DataAnalysisService, DataQueryService
from .gateways import (
    ExternalApiDatasetGateway,
    ExternalDataCatalogGateway,
    ExternalKnowledgeGateway,
    ExternalOneQueryGateway,
)
from .nl2sql_compiler import RestrictedIbisNl2SqlCompiler
from .logical_entity_validator import DataCatalogLogicalEntityValidator
from .scenario_registration import DataAnalysisScenarioRegistrationProvider


def _client() -> RuntimeHttpClient:
    return build_runtime_client()


def build_data_query_gateway() -> DataQueryService:
    client = _client()
    return DataQueryService(
        onequery_gateway=ExternalOneQueryGateway(client=client),
        api_gateway=ExternalApiDatasetGateway(client=client),
    )


def build_data_analysis_service() -> DataAnalysisService:
    client = _client()
    return DataAnalysisService(
        query_service=build_data_query_gateway(),
        data_catalog_gateway=ExternalDataCatalogGateway(client=client),
        knowledge_gateway=ExternalKnowledgeGateway(
            client=client,
            configuration=get_knowledge_configuration(),
        ),
        guardrail_gateway=ExternalGuardrailGateway(client=_client()),
        ai_gateway=OpenAICompatGateway(),
        completion_config_builder=build_completion_provider_config,
        prompt_catalog=get_prompt_catalog(),
        nl2sql_compiler=RestrictedIbisNl2SqlCompiler(),
        logical_entity_validator=DataCatalogLogicalEntityValidator(),
        audit_publisher=audit_publisher,
    )


def build_data_analysis_scenario_provider(service: DataAnalysisService | None = None) -> DataAnalysisScenarioRegistrationProvider:
    return DataAnalysisScenarioRegistrationProvider(service=service or build_data_analysis_service())
