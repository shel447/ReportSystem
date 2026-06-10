from src.infrastructure.dev_support import DevSupportService
from src.main import create_app
from tests.support.tornado_client import TornadoTestClient


def test_system_settings_handlers_use_dev_support_service(tmp_path, monkeypatch):
    monkeypatch.setattr(DevSupportService, "get_settings", lambda self: {"is_ready": False})
    monkeypatch.setattr(DevSupportService, "update_settings", lambda self, payload: {"is_ready": True})
    monkeypatch.setattr(DevSupportService, "test_settings", lambda self, target: {"target": target})
    payload = {"completion": {}, "embedding": {}}
    with TornadoTestClient(create_app(frontend_dir=str(tmp_path))) as client:
        assert client.get("/rest/dev/system-settings").json()["is_ready"] is False
        assert client.put("/rest/dev/system-settings", json=payload).json()["is_ready"] is True
        assert client.post("/rest/dev/system-settings/test", json={"target": "both"}).json()["target"] == "both"
