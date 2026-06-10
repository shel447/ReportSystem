from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from src.shared.kernel.authenticated import authenticated, get_authenticated_metadata
from src.shared.kernel.errors import ErrorCode, PermissionDeniedError


class Gateway:
    def __init__(self, denied=False):
        self.denied = denied
        self.calls = []

    def authenticate(self, **kwargs):
        self.calls.append(kwargs)
        if self.denied:
            raise PermissionDeniedError("auth failed")


class Server:
    def __init__(self, gateway):
        self.policy_auth_gateway = gateway
        self.audit_events = []
        self.audit_dispatcher = SimpleNamespace(submit=self.audit_events.append)

    async def run_blocking(self, call, *args, **kwargs):
        return call(*args, **kwargs)


class Controller:
    def __init__(self, gateway):
        self.server = Server(gateway)

    @authenticated(origin_url="/items", privilege=["dte.bi.chat.edit"])
    async def endpoint(self, req):
        return {"ok": True}


def request():
    return SimpleNamespace(
        current_user_id="user_001",
        request=SimpleNamespace(headers={"X-User-Id": "user_001"}),
    )


def test_authenticated_calls_gateway(monkeypatch):
    monkeypatch.delenv("REPORT_POLICY_AUTH_DISABLED", raising=False)
    gateway = Gateway()
    controller = Controller(gateway)

    assert asyncio.run(controller.endpoint(request())) == {"ok": True}
    assert gateway.calls[0]["privileges"] == ["dte.bi.chat.edit"]
    assert get_authenticated_metadata(controller.endpoint).origin_url == "/items"


def test_authenticated_denial_uses_public_error(monkeypatch):
    monkeypatch.delenv("REPORT_POLICY_AUTH_DISABLED", raising=False)
    controller = Controller(Gateway(denied=True))
    with pytest.raises(PermissionDeniedError) as exc:
        asyncio.run(controller.endpoint(request()))
    assert exc.value.error_code == ErrorCode.BASE_PERMISSION_DENIED
    assert controller.server.audit_events[0].kind == "security"
