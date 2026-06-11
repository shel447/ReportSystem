"""External platform privilege authentication adapter."""

from __future__ import annotations

import uuid

from ...shared.kernel.errors import ErrorCode, PermissionDeniedError, UpstreamError
from ...shared.kernel.authenticated import AuthenticationGateway
from .client import RuntimeHttpClient

POLICY_AUTH_PATH = "/rest/plat/priv/v1/policy/authentication"


class ExternalPolicyAuthenticationGateway(AuthenticationGateway):
    def __init__(self, *, client: RuntimeHttpClient) -> None:
        self._client = client

    def authenticate(
        self,
        *,
        user_id: str,
        privileges: list[str],
        origin_url: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        request_ids = [uuid.uuid4().hex for _ in privileges]
        payload = {
            "userId": user_id,
            "requests": [
                {"requestId": request_id, "action": privilege}
                for request_id, privilege in zip(request_ids, privileges, strict=True)
            ],
        }
        response = self._client.post_json(path_or_url=POLICY_AUTH_PATH, payload=payload, user_id=user_id)
        results = response.get("results")
        if (
            not isinstance(results, list)
            or len(results) != len(privileges)
            or any(not isinstance(item, dict) or not isinstance(item.get("result"), bool) for item in results)
        ):
            raise UpstreamError(
                "外部服务响应格式无效。",
                details={"url": POLICY_AUTH_PATH, "originUrl": origin_url},
                error_code=ErrorCode.BASE_UPSTREAM_INVALID_RESPONSE,
                source="platform",
                http_status=502,
            )
        if any(item["result"] is False for item in results):
            raise PermissionDeniedError(
                "auth failed",
                details={"originUrl": origin_url, "privileges": list(privileges)},
                error_code=ErrorCode.BASE_PERMISSION_DENIED,
                category="auth",
                http_status=403,
            )
