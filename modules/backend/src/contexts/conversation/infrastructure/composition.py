"""Composition builder for the conversation context."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.orm import Session

from ....infrastructure.platform.guardrail import ExternalGuardrailGateway
from ....infrastructure.platform.http_client import PlatformHttpClient
from ....infrastructure.platform.runtime import audit_dispatcher, build_platform_client
from ....shared.agentflow import InMemoryFlowRuntime
from ..application.scenarios import ScenarioDispatchService, ScenarioRegistry, ScenarioRegistrationProvider
from ..application.services import ConversationFlowRegistry, ConversationService
from .agentcore import ExternalConversationHistoryGateway


_FLOW_RUNTIME = InMemoryFlowRuntime()
_FLOW_REGISTRY = ConversationFlowRegistry()


def _client(*, service_key: str | None = None) -> PlatformHttpClient:
    return build_platform_client(service_key=service_key)


def build_conversation_service(
    db: Session,
    *,
    scenario_providers: Iterable[ScenarioRegistrationProvider],
) -> ConversationService:
    registry = ScenarioRegistry()
    for provider in scenario_providers:
        registry.register(provider.registration())
    registry.seal()
    return ConversationService(
        history_gateway=ExternalConversationHistoryGateway(client=_client(service_key="agentcore")),
        guardrail_gateway=ExternalGuardrailGateway(client=_client(service_key="guardrail")),
        scenario_dispatcher=ScenarioDispatchService(registry=registry),
        flow_runtime=_FLOW_RUNTIME,
        flow_registry=_FLOW_REGISTRY,
        audit_dispatcher=audit_dispatcher,
    )
