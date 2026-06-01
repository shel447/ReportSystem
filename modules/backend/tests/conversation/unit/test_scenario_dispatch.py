from dataclasses import dataclass

import pytest

from src.contexts.conversation.application.scenarios import (
    ScenarioDispatchService,
    ScenarioRegistration,
    ScenarioRegistry,
    ScenarioResult,
)
from src.contexts.conversation.application.models import ChatCommand
from src.contexts.conversation.application.services import ConversationService
from src.contexts.conversation.domain.models import ChatContext, ScenarioTrace
from src.shared.kernel.errors import ValidationError


@dataclass
class _Handler:
    calls: list

    def handle(self, *, command: object):
        self.calls.append(command)
        return ScenarioResult(status="finished")


class _Codec:
    def decode(self, *, context: ChatContext, payload: dict):
        return context, payload


def _registration(*, key="report", instructions=None, handler=None):
    instructions = instructions or {"generate_report", "extract_report_template"}
    return ScenarioRegistration(
        key=key,
        name="报告生成",
        description="生成报告",
        instructions=instructions,
        default_instruction=next(iter(instructions)),
        stateless_instructions={"extract_report_template"} & instructions,
        keywords={"报告", "日报"},
        examples={"帮我生成网络日报"},
        codec=_Codec(),
        handler=handler or _Handler([]),
    )


def _dispatcher(*registrations):
    registry = ScenarioRegistry()
    for registration in registrations:
        registry.register(registration)
    registry.seal()
    return ScenarioDispatchService(registry=registry)


def test_registry_rejects_duplicate_key_and_instruction():
    registry = ScenarioRegistry()
    registry.register(_registration())
    with pytest.raises(ValueError, match="Duplicate scenario key"):
        registry.register(_registration())
    with pytest.raises(ValueError, match="Duplicate scenario instruction"):
        registry.register(_registration(key="other", instructions={"generate_report"}))


def test_explicit_instruction_routes_exact_scenario_and_marks_stateless():
    dispatcher = _dispatcher(_registration())
    resolution = dispatcher.resolve(
        instruction="extract_report_template",
        question=None,
        reply_source_trace=None,
        previous_trace=None,
    )
    assert resolution.key == "report"
    assert resolution.source == "explicit_instruction"
    assert dispatcher.is_stateless(resolution)


def test_reply_source_wins_and_previous_waiting_turn_continues():
    dispatcher = _dispatcher(_registration())
    reply = dispatcher.resolve(
        instruction=None,
        question="补充信息",
        reply_source_trace=ScenarioTrace(key="report", resolution="local_recognizer", confidence=0.8, instruction="generate_report"),
        previous_trace=None,
    )
    assert reply.key == "report"
    assert reply.source == "reply_source"

    continued = dispatcher.resolve(
        instruction=None,
        question="继续",
        reply_source_trace=None,
        previous_trace=ScenarioTrace(
            key="report",
            resolution="explicit_instruction",
            confidence=1.0,
            continuation_state="waiting_user",
            instruction="generate_report",
        ),
    )
    assert continued.key == "report"
    assert continued.source == "previous_turn"


def test_local_recognizer_matches_report_and_unmatched_returns_clarification():
    dispatcher = _dispatcher(_registration())
    matched = dispatcher.resolve(instruction=None, question="请生成本月网络运行报告", reply_source_trace=None, previous_trace=None)
    assert matched.key == "report"
    assert matched.source == "local_recognizer"

    unmatched = dispatcher.resolve(instruction=None, question="你好", reply_source_trace=None, previous_trace=None)
    assert unmatched.key is None
    result = dispatcher.dispatch(
        resolution=unmatched,
        context=ChatContext(
            conversation_id="conv_001",
            chat_id="chat_001",
            user_id="default",
            instruction=None,
            scenario_key=None,
        ),
        payload={},
    )
    assert result.ask.type == "clarify_scenario"


def test_unknown_explicit_instruction_is_rejected():
    dispatcher = _dispatcher(_registration())
    with pytest.raises(ValidationError, match="Unsupported instruction"):
        dispatcher.resolve(instruction="unknown", question=None, reply_source_trace=None, previous_trace=None)


def test_stateless_instruction_does_not_create_conversation_messages():
    dispatcher = _dispatcher(_registration())

    class _NoWriteRepository:
        def __getattr__(self, name):
            raise AssertionError(f"stateless dispatch must not call repository method: {name}")

    response = ConversationService(
        conversation_repository=_NoWriteRepository(),
        chat_repository=_NoWriteRepository(),
        scenario_dispatcher=dispatcher,
    ).chat(
        data=ChatCommand(instruction="extract_report_template", question="解析模板"),
        user_id="default",
    )
    assert response.status == "finished"
