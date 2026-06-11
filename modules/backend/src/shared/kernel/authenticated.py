"""Route authentication annotation and platform privilege enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
import os
from typing import Callable, Protocol

from .errors import PermissionDeniedError
from .http import resolve_user_id
from .audit import AuditEvent


AUTHENTICATED_ATTR = "__chatbi_authenticated__"


@dataclass(frozen=True, slots=True)
class AuthenticatedMetadata:
    origin_url: str
    privilege: tuple[str, ...]


class AuthenticationGateway(Protocol):
    def authenticate(
        self,
        *,
        user_id: str,
        privileges: list[str],
        origin_url: str,
        headers: dict[str, str] | None = None,
    ) -> None: ...


def authenticated(*, origin_url: str, privilege: list[str]):
    metadata = AuthenticatedMetadata(origin_url=origin_url, privilege=tuple(privilege))

    def decorator(func):
        @wraps(func)
        async def wrapper(controller, req, *args, **kwargs):
            user_id = resolve_user_id(getattr(req, "current_user_id", None))
            if str(os.getenv("REPORT_POLICY_AUTH_DISABLED") or "").strip().lower() in {"1", "true", "yes", "on"}:
                return await func(controller, req, *args, **kwargs)
            try:
                await controller.server.run_blocking(
                    controller.server.policy_auth_gateway.authenticate,
                    user_id=user_id,
                    privileges=list(metadata.privilege),
                    origin_url=metadata.origin_url,
                    headers=dict(req.request.headers),
                )
            except PermissionDeniedError:
                controller.server.audit_publisher.submit(
                    AuditEvent(
                        user_id=user_id,
                        operation="authentication.denied",
                        target_obj=metadata.origin_url,
                        result="FAILED",
                        detail=f"auth failed: {','.join(metadata.privilege)}",
                        kind="security",
                    )
                )
                raise
            return await func(controller, req, *args, **kwargs)

        setattr(wrapper, AUTHENTICATED_ATTR, metadata)
        return wrapper

    return decorator


def get_authenticated_metadata(endpoint) -> AuthenticatedMetadata | None:
    return getattr(endpoint, AUTHENTICATED_ATTR, None)
