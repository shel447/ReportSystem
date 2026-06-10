from __future__ import annotations

import pytest

from src.shared.kernel.errors import ErrorCode, PermissionDeniedError
from src.shared.kernel.policy_auth import PolicyAuthenticationRequest, PolicyAuthenticationResult, enforce_policy_auth, policy_auth


class RecordingGateway:
    def __init__(self, allowed=True):
        self.allowed = allowed
        self.calls = []

    def authenticate(self, request: PolicyAuthenticationRequest) -> PolicyAuthenticationResult:
        self.calls.append(request)
        return PolicyAuthenticationResult(allowed=self.allowed, upstream_code=None if self.allowed else "naie.denied")


@policy_auth(resource="item", action="list")
def endpoint():
    pass


def test_policy_auth_calls_gateway_with_framework_neutral_request(monkeypatch):
    monkeypatch.delenv("REPORT_POLICY_AUTH_DISABLED", raising=False)
    gateway = RecordingGateway()
    enforce_policy_auth(endpoint=endpoint, user_id="user_001", method="GET", path="/items", headers={"X-User-Id": "user_001", "Host": "local"}, gateway=gateway)
    assert gateway.calls[0].resource == "item"
    assert "Host" not in gateway.calls[0].headers


def test_policy_auth_denial_uses_public_error(monkeypatch):
    monkeypatch.delenv("REPORT_POLICY_AUTH_DISABLED", raising=False)
    with pytest.raises(PermissionDeniedError) as exc:
        enforce_policy_auth(endpoint=endpoint, user_id="user_001", method="GET", path="/items", headers={}, gateway=RecordingGateway(False))
    assert exc.value.error_code == ErrorCode.BASE_PERMISSION_DENIED
