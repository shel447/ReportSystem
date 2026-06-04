"""Shared safety-check contracts used by business contexts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class GuardrailResult:
    passed: bool
    reason: str = ""


class GuardrailGateway(Protocol):
    def check_question(self, question: str, *, user_id: str) -> GuardrailResult: ...
    def check_answer(self, answer: str, *, user_id: str) -> GuardrailResult: ...
    def check_application_security(self, *, kind: str, content: str, user_id: str) -> GuardrailResult: ...
