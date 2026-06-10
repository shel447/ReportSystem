from src.infrastructure.dev_support import DevSupportService
from src.main import create_app
from tests.support.tornado_client import TornadoTestClient


def test_feedback_handlers_use_dev_support_service(tmp_path, monkeypatch):
    monkeypatch.setattr(DevSupportService, "list_feedbacks", lambda self: [{"id": "fb_1"}])
    monkeypatch.setattr(DevSupportService, "create_feedback", lambda self, **kwargs: {"status": "success", "feedback_id": "fb_1"})
    monkeypatch.setattr(DevSupportService, "delete_feedback", lambda self, feedback_id: {"status": "success"})
    with TornadoTestClient(create_app(frontend_dir=str(tmp_path))) as client:
        assert client.get("/rest/dev/feedback/").json()[0]["id"] == "fb_1"
        assert client.post("/rest/dev/feedback/", json={"submitter": "u", "content": "c"}).json()["feedback_id"] == "fb_1"
        assert client.delete("/rest/dev/feedback/fb_1").status_code == 200
