from __future__ import annotations

import pytest

from src.infrastructure.platform.policy_auth import ExternalPolicyAuthenticationGateway, POLICY_AUTH_PATH
from src.shared.kernel.errors import ErrorCode, PermissionDeniedError, UpstreamError


class Client:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post_json(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def test_gateway_posts_privilege_requests():
    client = Client({"results": [{"result": True}, {"result": True}]})
    gateway = ExternalPolicyAuthenticationGateway(client=client)

    gateway.authenticate(user_id="user_001", privileges=["a", "b"], origin_url="/chat")

    call = client.calls[0]
    assert call["path_or_url"] == POLICY_AUTH_PATH
    assert call["payload"]["userId"] == "user_001"
    assert [item["action"] for item in call["payload"]["requests"]] == ["a", "b"]


def test_gateway_denies_when_any_result_is_false():
    gateway = ExternalPolicyAuthenticationGateway(client=Client({"results": [{"result": False}]}))
    with pytest.raises(PermissionDeniedError) as exc:
        gateway.authenticate(user_id="user", privileges=["a"], origin_url="/chat")
    assert exc.value.error_code == ErrorCode.BASE_PERMISSION_DENIED


@pytest.mark.parametrize("response", [{"results": []}, {"results": [{}]}, {"results": [{"result": "true"}]}])
def test_gateway_rejects_invalid_results(response):
    gateway = ExternalPolicyAuthenticationGateway(client=Client(response))
    with pytest.raises(UpstreamError) as exc:
        gateway.authenticate(user_id="user", privileges=["a"], origin_url="/chat")
    assert exc.value.error_code == ErrorCode.BASE_UPSTREAM_INVALID_RESPONSE
