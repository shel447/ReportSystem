"""Framework-neutral route-level policy authentication contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Any, Callable, Mapping, Protocol, TypeVar

from .errors import ApplicationError, ErrorCode, PermissionDeniedError


POLICY_AUTH_ATTR = "__chatbi_policy_auth__"


@dataclass(frozen=True, slots=True)
class PolicyAuthMetadata:
    resource: str
    action: str


@dataclass(frozen=True, slots=True)
class PolicyAuthenticationRequest:
    user_id: str
    method: str
    path: str
    resource: str
    action: str
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PolicyAuthenticationResult:
    allowed: bool
    upstream_code: str | None = None
    upstream_message: str | None = None


class PolicyAuthenticationGateway(Protocol):
    def authenticate(self, request: PolicyAuthenticationRequest) -> PolicyAuthenticationResult: ...


F = TypeVar("F", bound=Callable[..., Any])


def policy_auth(*, resource: str, action: str) -> Callable[[F], F]:
    """Annotate a public business route with the policy permission point."""

    metadata = PolicyAuthMetadata(resource=_required(resource, "resource"), action=_required(action, "action"))

    def decorator(func: F) -> F:
        setattr(func, POLICY_AUTH_ATTR, metadata)
        return func

    return decorator


def get_policy_auth_metadata(endpoint: Any) -> PolicyAuthMetadata | None:
    return getattr(endpoint, POLICY_AUTH_ATTR, None)


def route_policy_auth_metadata(endpoint: Any) -> PolicyAuthMetadata:
    metadata = get_policy_auth_metadata(endpoint)
    if metadata is None:
        raise ApplicationError(
            "接口缺少权限配置，请联系系统管理员。",
            error_code=ErrorCode.BASE_UNKNOWN,
            category="configuration",
            http_status=500,
        )
    return metadata


def enforce_policy_auth(
    *,
    endpoint: Any,
    user_id: str,
    method: str,
    path: str,
    headers: Mapping[str, str],
    gateway: PolicyAuthenticationGateway | None,
) -> None:
    metadata = route_policy_auth_metadata(endpoint)
    if _policy_auth_disabled_for_tests():
        return
    if gateway is None:
        raise ApplicationError(
            "权限校验服务未配置，请联系系统管理员。",
            error_code=ErrorCode.BASE_UNKNOWN,
            category="configuration",
            http_status=500,
        )
    result = gateway.authenticate(
        PolicyAuthenticationRequest(
            user_id=user_id,
            method=method.upper(),
            path=path,
            resource=metadata.resource,
            action=metadata.action,
            headers=_forwardable_headers(headers),
        )
    )
    if not result.allowed:
        details: dict[str, Any] = {}
        if result.upstream_code:
            details["upstreamCode"] = result.upstream_code
        if result.upstream_message:
            details["upstreamMessage"] = result.upstream_message
        raise PermissionDeniedError(
            "没有操作权限。",
            details=details,
            error_code=ErrorCode.BASE_PERMISSION_DENIED,
            category="auth",
            http_status=403,
        )


def _forwardable_headers(headers: Mapping[str, str]) -> dict[str, str]:
    excluded = {
        "connection",
        "content-length",
        "host",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
    return {key: value for key, value in headers.items() if key.lower() not in excluded}


def _required(value: str, name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"policy auth {name} is required")
    return normalized


def _policy_auth_disabled_for_tests() -> bool:
    return str(os.getenv("REPORT_POLICY_AUTH_DISABLED") or "").strip().lower() in {"1", "true", "yes", "on"}
