from __future__ import annotations

from src.infrastructure.platform.guardrail import ExternalGuardrailGateway


class _RecordingClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def post_json(self, *, path_or_url: str, payload: dict, user_id: str | None = None) -> dict:
        self.calls.append({"path_or_url": path_or_url, "payload": payload, "user_id": user_id})
        if path_or_url.endswith("/application-sec/check"):
            return {"results": [{"isLegal": True, "response": ""}]}
        return {"status": False, "error_msg": None}


def test_guardrail_gateway_uses_formal_naie_paths():
    client = _RecordingClient()
    gateway = ExternalGuardrailGateway(client=client)

    assert gateway.check_question("hello", user_id="user_001").passed is True
    assert gateway.check_answer("ok", user_id="user_001").passed is True
    assert gateway.check_application_security(kind="sql", content="select 1", user_id="user_001").passed is True

    assert [item["path_or_url"] for item in client.calls] == [
        "/rest/naie/guardrail/v1/question/check",
        "/rest/naie/guardrail/v1/answer/check",
        "/rest/naie/guardrail/v1/application-sec/check",
    ]
    assert all(item["user_id"] == "user_001" for item in client.calls)
