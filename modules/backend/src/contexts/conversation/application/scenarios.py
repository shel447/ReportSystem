"""通用对话的场景注册、识别和分发机制。"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Protocol

from ....shared.kernel.errors import ValidationError
from ....shared.agentflow import FlowGraph
from ..domain.models import ScenarioInvocationContext, ScenarioTrace


@dataclass(slots=True)
class ScenarioAskProjection:
    """业务场景投影到通用追问外壳的结果。"""

    mode: str
    type: str
    title: str
    text: str
    fields: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ScenarioAnswerProjection:
    """业务场景投影到通用答案外壳的结果。"""

    answer_type: str
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ScenarioResult:
    """业务场景完成一次推进后的通用结果。"""

    status: str
    ask: ScenarioAskProjection | None = None
    answer: ScenarioAnswerProjection | None = None
    conversation_title: str | None = None
    flow: FlowGraph | None = None


class ScenarioHandler(Protocol):
    """业务 Context 接入 conversation 时实现的严格处理协议。"""

    def handle(self, *, command: object) -> ScenarioResult: ...


class ScenarioCodec(Protocol):
    """把短暂存在于对话入口的原始字段解码为场景自己的严格命令。"""

    def decode(self, *, context: ScenarioInvocationContext, payload: dict[str, Any]) -> object: ...


class ScenarioRegistrationProvider(Protocol):
    """Business-owned provider that contributes one conversation scenario registration."""

    def registration(self) -> ScenarioRegistration: ...


class SemanticScenarioMatcher(Protocol):
    """为未来 embedding 或 LLM 分类器预留的语义匹配接口。"""

    def score(self, *, text: str, registration: "ScenarioRegistration") -> float: ...


@dataclass(slots=True)
class ScenarioRegistration:
    """业务模块在启动阶段提交的场景声明。"""

    key: str
    name: str
    description: str
    instructions: set[str]
    default_instruction: str
    codec: ScenarioCodec
    handler: ScenarioHandler
    stateless_instructions: set[str] = field(default_factory=set)
    keywords: set[str] = field(default_factory=set)
    examples: set[str] = field(default_factory=set)
    supports_continuation: bool = True
    priority: int = 0


@dataclass(slots=True)
class ScenarioResolution:
    """conversation 对本轮输入的场景判定。"""

    key: str | None
    instruction: str | None
    source: str
    confidence: float

    def to_trace(self, *, continuation_state: str | None = None) -> ScenarioTrace:
        return ScenarioTrace(
            key=self.key,
            resolution=self.source,
            confidence=self.confidence,
            continuation_state=continuation_state,
            instruction=self.instruction,
        )


class ScenarioRegistry:
    """启动期写入、运行期只读的场景注册表。"""

    def __init__(self) -> None:
        self._by_key: dict[str, ScenarioRegistration] = {}
        self._by_instruction: dict[str, ScenarioRegistration] = {}
        self._sealed = False

    def register(self, registration: ScenarioRegistration) -> None:
        if self._sealed:
            raise RuntimeError("Scenario registry is already sealed")
        key = registration.key.strip()
        if not key:
            raise ValueError("Scenario key is required")
        if key in self._by_key:
            raise ValueError(f"Duplicate scenario key: {key}")
        if registration.default_instruction not in registration.instructions:
            raise ValueError(f"Scenario {key} default instruction must be registered")
        for instruction in registration.instructions:
            if instruction in self._by_instruction:
                raise ValueError(f"Duplicate scenario instruction: {instruction}")
        self._by_key[key] = registration
        for instruction in registration.instructions:
            self._by_instruction[instruction] = registration

    def seal(self) -> None:
        self._sealed = True

    def get(self, key: str | None) -> ScenarioRegistration | None:
        return self._by_key.get(str(key or "").strip())

    def find_by_instruction(self, instruction: str | None) -> ScenarioRegistration | None:
        return self._by_instruction.get(str(instruction or "").strip())

    def list_all(self) -> list[ScenarioRegistration]:
        return list(self._by_key.values())


class ScenarioRecognizer:
    """使用本地可解释规则识别未显式指定的业务场景。"""

    def __init__(
        self,
        *,
        semantic_matcher: SemanticScenarioMatcher | None = None,
        minimum_confidence: float = 0.42,
        minimum_margin: float = 0.08,
    ) -> None:
        self.semantic_matcher = semantic_matcher
        self.minimum_confidence = minimum_confidence
        self.minimum_margin = minimum_margin

    def recognize(self, *, text: str, registrations: list[ScenarioRegistration]) -> ScenarioResolution:
        query = str(text or "").strip().lower()
        if not query:
            return ScenarioResolution(key=None, instruction=None, source="unmatched", confidence=0.0)
        scored = sorted(
            ((self._score(query=query, registration=item), item) for item in registrations),
            key=lambda item: (item[0], item[1].priority),
            reverse=True,
        )
        if not scored or scored[0][0] < self.minimum_confidence:
            return ScenarioResolution(key=None, instruction=None, source="unmatched", confidence=scored[0][0] if scored else 0.0)
        runner_up = scored[1][0] if len(scored) > 1 else 0.0
        if scored[0][0] - runner_up < self.minimum_margin:
            return ScenarioResolution(key=None, instruction=None, source="unmatched", confidence=scored[0][0])
        registration = scored[0][1]
        return ScenarioResolution(
            key=registration.key,
            instruction=registration.default_instruction,
            source="local_recognizer",
            confidence=scored[0][0],
        )

    def _score(self, *, query: str, registration: ScenarioRegistration) -> float:
        keyword_score = max((0.78 if keyword.lower() in query else 0.0 for keyword in registration.keywords), default=0.0)
        example_score = max((SequenceMatcher(None, query, item.lower()).ratio() * 0.72 for item in registration.examples), default=0.0)
        semantic_score = self.semantic_matcher.score(text=query, registration=registration) if self.semantic_matcher else 0.0
        return min(1.0, max(keyword_score, example_score, semantic_score) + max(0, registration.priority) * 0.01)


class ScenarioDispatchService:
    """按统一规则解析场景并调用对应业务 handler。"""

    def __init__(self, *, registry: ScenarioRegistry, recognizer: ScenarioRecognizer | None = None) -> None:
        self.registry = registry
        self.recognizer = recognizer or ScenarioRecognizer()

    def resolve(
        self,
        *,
        instruction: str | None,
        question: str | None,
        reply_source_trace: ScenarioTrace | None,
        previous_trace: ScenarioTrace | None,
    ) -> ScenarioResolution:
        normalized_instruction = str(instruction or "").strip()
        if normalized_instruction:
            registration = self.registry.find_by_instruction(normalized_instruction)
            if registration is None:
                raise ValidationError(f"Unsupported instruction: {normalized_instruction}")
            return ScenarioResolution(
                key=registration.key,
                instruction=normalized_instruction,
                source="explicit_instruction",
                confidence=1.0,
            )
        if reply_source_trace is not None and reply_source_trace.key:
            registration = self.registry.get(reply_source_trace.key)
            if registration is not None:
                return ScenarioResolution(
                    key=registration.key,
                    instruction=reply_source_trace.instruction or registration.default_instruction,
                    source="reply_source",
                    confidence=1.0,
                )
        if previous_trace is not None and previous_trace.key and previous_trace.continuation_state == "waiting_user":
            registration = self.registry.get(previous_trace.key)
            if registration is not None and registration.supports_continuation:
                return ScenarioResolution(
                    key=registration.key,
                    instruction=previous_trace.instruction or registration.default_instruction,
                    source="previous_turn",
                    confidence=1.0,
                )
        return self.recognizer.recognize(text=str(question or ""), registrations=self.registry.list_all())

    def is_stateless(self, resolution: ScenarioResolution) -> bool:
        registration = self.registry.get(resolution.key)
        return bool(registration and resolution.instruction in registration.stateless_instructions)

    def dispatch(self, *, resolution: ScenarioResolution, context: ScenarioInvocationContext, payload: dict[str, Any]) -> ScenarioResult:
        registration = self.registry.get(resolution.key)
        if registration is None:
            return ScenarioResult(
                status="waiting_user",
                ask=ScenarioAskProjection(
                    mode="natural_language",
                    type="clarify_scenario",
                    title="请补充你的需求",
                    text="请再说明希望系统帮助你完成什么任务。",
                ),
            )
        return registration.handler.handle(command=registration.codec.decode(context=context, payload=payload))
