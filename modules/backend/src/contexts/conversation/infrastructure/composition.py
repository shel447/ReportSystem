"""Composition builder for the conversation context."""

from __future__ import annotations

from collections.abc import Iterable

from ....infrastructure.platform.guardrail import ExternalGuardrailGateway
from ....infrastructure.platform.http_client import PlatformHttpClient
from ....infrastructure.platform.runtime import audit_dispatcher, build_platform_client
from ....shared.agentflow import InMemoryFlowRuntime, SubflowSpec
from ..application.scenarios import ScenarioDispatchService, ScenarioRegistry, ScenarioRegistrationProvider
from ..application.services import ConversationFlowRegistry, ConversationService
from .agentcore import ExternalConversationHistoryGateway


_FLOW_RUNTIME = InMemoryFlowRuntime()
_FLOW_REGISTRY = ConversationFlowRegistry()


def _client(*, service_key: str | None = None) -> PlatformHttpClient:
    return build_platform_client(service_key=service_key)


def build_conversation_service(
    *,
    scenario_providers: Iterable[ScenarioRegistrationProvider],
    subflow_specs: Iterable[SubflowSpec] = (),
) -> ConversationService:
    _register_subflows(subflow_specs)
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


def _register_subflows(specs: Iterable[SubflowSpec]) -> None:
    for spec in specs:
        try:
            _FLOW_RUNTIME.subflow_registry.get(spec.name)
        except ValueError:
            _FLOW_RUNTIME.subflow_registry.register(spec)
