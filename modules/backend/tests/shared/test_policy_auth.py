from __future__ import annotations

from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from src.main import register_error_handlers
from src.shared.kernel.errors import ErrorCode
from src.shared.kernel.http import get_current_user_id
from src.shared.kernel.policy_auth import (
    PolicyAuthenticationRequest,
    PolicyAuthenticationResult,
    enforce_policy_auth,
    policy_auth,
)


class _RecordingGateway:
    def __init__(self, *, allowed: bool = True) -> None:
        self.allowed = allowed
        self.calls: list[PolicyAuthenticationRequest] = []

    def authenticate(self, request: PolicyAuthenticationRequest) -> PolicyAuthenticationResult:
        self.calls.append(request)
        return PolicyAuthenticationResult(
            allowed=self.allowed,
            upstream_code=None if self.allowed else "naie.priv.permission.denied",
            upstream_message=None if self.allowed else "denied",
        )


def _client(gateway: _RecordingGateway, *, annotated: bool = True) -> TestClient:
    router = APIRouter(prefix="/items")

    if annotated:
        @router.get("")
        @policy_auth(resource="item", action="list")
        def list_items():
            return {"ok": True}
    else:
        @router.get("")
        def list_items():
            return {"ok": True}

    app = FastAPI()
    app.state.policy_auth_gateway = gateway
    register_error_handlers(app)
    app.include_router(router, prefix="/rest/chatbi/v1", dependencies=[Depends(get_current_user_id), Depends(enforce_policy_auth)])
    return TestClient(app)


def test_policy_auth_dependency_calls_gateway_with_route_metadata_and_headers(monkeypatch):
    monkeypatch.delenv("REPORT_POLICY_AUTH_DISABLED", raising=False)
    gateway = _RecordingGateway(allowed=True)
    client = _client(gateway)

    response = client.get(
        "/rest/chatbi/v1/items",
        headers={
            "X-User-Id": "user_001",
            "Authorization": "Bearer token",
            "Content-Length": "123",
        },
    )

    assert response.status_code == 200
    call = gateway.calls[0]
    assert call.user_id == "user_001"
    assert call.method == "GET"
    assert call.path == "/rest/chatbi/v1/items"
    assert call.resource == "item"
    assert call.action == "list"
    assert call.headers["x-user-id"] == "user_001"
    assert call.headers["authorization"] == "Bearer token"
    assert "content-length" not in call.headers
    assert "host" not in call.headers


def test_policy_auth_denial_returns_public_permission_error(monkeypatch):
    monkeypatch.delenv("REPORT_POLICY_AUTH_DISABLED", raising=False)
    client = _client(_RecordingGateway(allowed=False))

    response = client.get("/rest/chatbi/v1/items", headers={"X-User-Id": "user_001"})

    assert response.status_code == 403
    assert response.json()["errorCode"] == ErrorCode.BASE_PERMISSION_DENIED
    assert response.json()["errorMsg"] == "没有操作权限。"
    assert response.json()["details"]["upstreamCode"] == "naie.priv.permission.denied"


def test_policy_auth_missing_route_annotation_fails_closed(monkeypatch):
    monkeypatch.delenv("REPORT_POLICY_AUTH_DISABLED", raising=False)
    client = _client(_RecordingGateway(allowed=True), annotated=False)

    response = client.get("/rest/chatbi/v1/items", headers={"X-User-Id": "user_001"})

    assert response.status_code == 500
    assert response.json()["errorCode"] == ErrorCode.BASE_UNKNOWN
