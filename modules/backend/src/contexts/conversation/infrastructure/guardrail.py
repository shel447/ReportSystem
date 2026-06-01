"""Adapter for AgentCore guardrail endpoints."""

from __future__ import annotations

import os

from ..application.ports import GuardrailResult
from ....shared.kernel.errors import UpstreamError


class ExternalGuardrailGateway:
    def __init__(self, *, client) -> None:
        self.client = client

    def check_question(self, question: str, *, user_id: str) -> GuardrailResult:
        if _disabled():
            return GuardrailResult(passed=True)
        payload = self.client.post_json(
            path_or_url="/rest/naie/guardrail/v1/question/check",
            payload={"questions": [question]},
            user_id=user_id,
        )
        return _legal_check_result(payload)

    def check_answer(self, answer: str, *, user_id: str) -> GuardrailResult:
        if _disabled():
            return GuardrailResult(passed=True)
        payload = self.client.post_json(
            path_or_url="/rest/naie/guardrail/v1/answer/check",
            payload={"answers": [answer]},
            user_id=user_id,
        )
        return _legal_check_result(payload)

    def check_application_security(self, *, kind: str, content: str, user_id: str) -> GuardrailResult:
        if _disabled():
            return GuardrailResult(passed=True)
        payload = self.client.post_json(
            path_or_url="/rest/naie/guardrail/v1/application-sec/check",
            payload={"type": kind, "content": content},
            user_id=user_id,
        )
        if "status" not in payload:
            raise UpstreamError("guardrail response status is required")
        return GuardrailResult(passed=not bool(payload.get("status")), reason=str(payload.get("error_msg") or ""))


def _legal_check_result(payload: dict) -> GuardrailResult:
    results = payload.get("checkResults")
    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        raise UpstreamError("guardrail response checkResults is required")
    return GuardrailResult(passed=bool(results[0].get("isLegal")), reason=str(results[0].get("response") or ""))


def _disabled() -> bool:
    return str(os.getenv("REPORT_GUARDRAIL_DISABLED") or "").strip().lower() in {"1", "true", "yes"}
