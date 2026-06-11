from __future__ import annotations

from types import SimpleNamespace

from src.contexts.conversation.application.models import ChatAnswerEnvelope, ChatResponse, ChatStreamEvent, SessionDetail
from tests.support.tornado_client import create_app
from src.shared.messaging import InteractionStep
from tests.support.tornado_client import FakeWebContainer, TornadoTestClient


class ConversationService:
    def list_sessions(self, *, user_id):
        return []

    def get_session(self, *, conversation_id, user_id):
        return SessionDetail(conversation_id=conversation_id, title="会话", status="active", records=[])

    def chat(self, *, data, user_id):
        return ChatResponse(conversation_id="conv_1", chat_id="chat_1", status="finished", steps=[], ask=None, answer=ChatAnswerEnvelope(answer_type="TEXT", payload={"text": "ok"}), errors=[], timestamp=1)

    def chat_stream(self, *, data, user_id):
        yield ChatStreamEvent(conversation_id="conv_1", chat_id="chat_1", sequence=1, event_type="step_delta", status="running", step=InteractionStep(step_id="step", title="处理中"))
        yield ChatStreamEvent(conversation_id="conv_1", chat_id="chat_1", sequence=2, event_type="done", status="finished")

    def stop_chat(self, *, chat_id, user_id):
        return True


def test_health_check_requires_no_identity(tmp_path):
    with TornadoTestClient(create_app(frontend_dir=str(tmp_path), container=FakeWebContainer())) as client:
        response = client.get("/rest/chatbi/healthcheck")
        assert response.status_code == 200
        assert response.json() == {"retCode": 0, "retInfo": "chatbi works well"}


def test_chat_json_and_history_contract(tmp_path):
    container = FakeWebContainer(conversation_service=ConversationService())
    with TornadoTestClient(create_app(frontend_dir=str(tmp_path), container=container), headers={"X-User-Id": "user"}) as client:
        response = client.post("/rest/chatbi/v1/chat", json={"question": "hello"})
        assert response.status_code == 200
        assert response.json()["answer"]["answerType"] == "TEXT"
        history = client.get("/rest/chatbi/v1/chat/detail", params={"conversationId": "conv_1"}).json()
        assert history["conversationId"] == "conv_1"
        assert "records" in history


def test_chat_sse_preserves_event_order(tmp_path):
    with TornadoTestClient(create_app(frontend_dir=str(tmp_path), container=FakeWebContainer(conversation_service=ConversationService())), headers={"X-User-Id": "user"}) as client:
        response = client.post("/rest/chatbi/v1/chat", headers={"Accept": "text/event-stream"}, json={"question": "hello"})
        assert response.status_code == 200
        assert response.text.index('"sequence": 1') < response.text.index('"sequence": 2')
        assert '"eventType": "step_delta"' in response.text


def test_chat_query_parameters_are_required_and_legacy_paths_are_removed(tmp_path):
    container = FakeWebContainer(conversation_service=ConversationService())
    with TornadoTestClient(create_app(frontend_dir=str(tmp_path), container=container), headers={"X-User-Id": "user"}) as client:
        missing = client.get("/rest/chatbi/v1/chat/detail")
        duplicate = client.get("/rest/chatbi/v1/chat/detail?conversationId=one&conversationId=two")
        legacy = client.get("/rest/chatbi/v1/chat/conv_1")
    assert missing.status_code == 400
    assert missing.json()["errorCode"] == "chatbi.base.param.invalid"
    assert duplicate.status_code == 400
    assert duplicate.json()["errorCode"] == "chatbi.base.param.invalid"
    assert legacy.status_code == 404
