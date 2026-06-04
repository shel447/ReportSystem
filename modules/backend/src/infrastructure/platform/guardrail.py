"""Platform Guardrail adapter shared by business contexts."""

from __future__ import annotations

from ...shared.kernel.safety import GuardrailResult


class ExternalGuardrailGateway:
    def __init__(self, *, client) -> None:
        self.client = client

    def check_question(self, question: str, *, user_id: str) -> GuardrailResult:
        if not str(question or "").strip():
            return GuardrailResult(passed=True)
        payload = self.client.post_json(
            path_or_url="/rest/naie/guardrail/v1/question/check",
            payload={"question": question},
            user_id=user_id,
        )
        return _check_result(payload)

    def check_answer(self, answer: str, *, user_id: str) -> GuardrailResult:
        if not str(answer or "").strip():
            return GuardrailResult(passed=True)
        payload = self.client.post_json(
            path_or_url="/rest/naie/guardrail/v1/answer/check",
            payload={"answer": answer},
            user_id=user_id,
        )
        return _check_result(payload)

    def check_application_security(self, *, kind: str, content: str, user_id: str) -> GuardrailResult:
        if not str(content or "").strip():
            return GuardrailResult(passed=True)
        payload = self.client.post_json(
            path_or_url="/rest/naie/guardrail/v1/application-sec/check",
            payload={"kind": kind, "content": content},
            user_id=user_id,
        )
        return _legal_check_result(payload)


def _check_result(payload: dict) -> GuardrailResult:
    return GuardrailResult(passed=not bool(payload.get("status")), reason=str(payload.get("error_msg") or ""))


def _legal_check_result(payload: dict) -> GuardrailResult:
    results = list(payload.get("results") or [])
    if not results:
        return GuardrailResult(passed=True)
    return GuardrailResult(passed=bool(results[0].get("isLegal")), reason=str(results[0].get("response") or ""))
