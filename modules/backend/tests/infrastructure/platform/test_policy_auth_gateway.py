from __future__ import annotations

import httpx
import pytest

from src.infrastructure.platform.http_client import ExternalServiceConfig, PlatformHttpClient
from src.infrastructure.platform.policy_auth import ExternalPolicyAuthenticationGateway, POLICY_AUTH_PATH
from src.shared.kernel.errors import ErrorCode, UpstreamError
from src.shared.kernel.policy_auth import PolicyAuthenticationRequest


class _FakeClient:
    calls: list[dict[str, object]] = []
    response: httpx.Response | Exception = httpx.Response(200, json={"allowed": True})

    def __init__(self, *args, **kwargs) -> None:
        self.timeout = kwargs.get("timeout")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url: str, *, headers: dict[str, str]):
        self.calls.append({"method": "GET", "url": url, "headers": dict(headers)})
        if isinstance(self.response, Exception):
            raise self.response
        self.response.request = httpx.Request("GET", url)
        return self.response


def _gateway() -> ExternalPolicyAuthenticationGateway:
    return ExternalPolicyAuthenticationGateway(
        client=PlatformHttpClient(config=ExternalServiceConfig(base_url="http://platform.example", timeout_seconds=3))
    )


def _request(headers: dict[str, str] | None = None) -> PolicyAuthenticationRequest:
    return PolicyAuthenticationRequest(
        user_id="user_001",
        method="POST",
        path="/rest/chatbi/v1/chat",
        resource="chat",
        action="create",
        headers=headers or {"x-user-id": "user_001", "authorization": "Bearer token"},
    )


def test_policy_auth_gateway_uses_get_formal_path_and_forwards_headers(monkeypatch):
    _FakeClient.calls = []
    _FakeClient.response = httpx.Response(200, json={"allowed": True})
    monkeypatch.setattr("src.infrastructure.platform.policy_auth.httpx.Client", _FakeClient)

    result = _gateway().authenticate(_request())

    assert result.allowed is True
    assert _FakeClient.calls == [
        {
            "method": "GET",
            "url": f"http://platform.example{POLICY_AUTH_PATH}",
            "headers": {"x-user-id": "user_001", "authorization": "Bearer token"},
        }
    ]


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(403, json={"errorCode": "naie.priv.permission.denied", "errorMsg": "denied"}),
        httpx.Response(200, json={"allowed": False, "errorCode": "naie.priv.permission.denied", "errorMsg": "denied"}),
        httpx.Response(200, json={"retCode": 1001, "retInfo": "denied"}),
    ],
)
def test_policy_auth_gateway_maps_denial_to_result(monkeypatch, response):
    _FakeClient.calls = []
    _FakeClient.response = response
    monkeypatch.setattr("src.infrastructure.platform.policy_auth.httpx.Client", _FakeClient)

    result = _gateway().authenticate(_request())

    assert result.allowed is False
    assert result.upstream_code in {"naie.priv.permission.denied", "1001"}


def test_policy_auth_gateway_fails_closed_when_upstream_errors(monkeypatch):
    _FakeClient.calls = []
    _FakeClient.response = httpx.Response(500, json={"errorCode": "naie.platform.error"})
    monkeypatch.setattr("src.infrastructure.platform.policy_auth.httpx.Client", _FakeClient)

    with pytest.raises(UpstreamError) as ctx:
        _gateway().authenticate(_request())

    assert ctx.value.error_code == ErrorCode.BASE_UPSTREAM_UNAVAILABLE
    assert ctx.value.details["upstreamCode"] == "naie.platform.error"


def test_policy_auth_gateway_times_out_as_base_overtime(monkeypatch):
    _FakeClient.calls = []
    _FakeClient.response = httpx.TimeoutException("timeout")
    monkeypatch.setattr("src.infrastructure.platform.policy_auth.httpx.Client", _FakeClient)

    with pytest.raises(UpstreamError) as ctx:
        _gateway().authenticate(_request())

    assert ctx.value.error_code == ErrorCode.BASE_OVERTIME
