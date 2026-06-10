"""Shared Tornado RequestHandler mechanics."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, ValidationError as PydanticValidationError
from tornado import web

from ..shared.kernel.errors import ApplicationError, ErrorCode, error_response_payload, http_status_for
from ..shared.kernel.http import resolve_user_id
from ..shared.kernel.policy_auth import enforce_policy_auth

T = TypeVar("T")


class BaseHandler(web.RequestHandler):
    """Framework boundary shared by every ReportSystem request."""

    require_identity = False
    require_policy_auth = False

    def initialize(self, *, container=None) -> None:
        self.container = container or self.application.settings.get("container")
        self.user_id: str | None = None

    async def prepare(self) -> None:
        if self.require_identity:
            self.user_id = resolve_user_id(self.request.headers.get("X-User-Id"))
        if self.require_policy_auth:
            endpoint = getattr(self, self.request.method.lower(), None)
            await self.run_blocking(
                enforce_policy_auth,
                endpoint=endpoint,
                user_id=self.user_id or "",
                method=self.request.method,
                path=self.request.path,
                headers=dict(self.request.headers),
                gateway=getattr(self.container, "policy_auth_gateway", None),
            )

    def parse_json(self, model: type[T]) -> T:
        try:
            payload = json.loads(self.request.body or b"{}")
            if issubclass(model, BaseModel):
                return model.model_validate(payload)
            return model(**payload)
        except (json.JSONDecodeError, PydanticValidationError, TypeError, ValueError) as exc:
            details = {"errors": exc.errors()} if isinstance(exc, PydanticValidationError) else {"reason": str(exc)}
            raise ApplicationError(
                "输入参数校验失败，请检查请求内容。",
                details=details,
                error_code=ErrorCode.BASE_PARAM_INVALID,
                category="param",
                http_status=400,
            ) from exc

    async def run_blocking(self, call: Callable[..., T], *args, **kwargs) -> T:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.container.executor, lambda: call(*args, **kwargs))

    def write_json(self, payload: Any, *, status: int = 200) -> None:
        self.set_status(status)
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.finish(json.dumps(payload, ensure_ascii=False))

    def write_error(self, status_code: int, **kwargs) -> None:
        exc_info = kwargs.get("exc_info")
        exc = exc_info[1] if exc_info else None
        if isinstance(exc, ApplicationError) or self.request.path.startswith("/rest/chatbi/v1"):
            public_exc = exc
            if isinstance(exc, web.HTTPError):
                public_exc = ApplicationError(
                    exc.reason or "请求处理失败。",
                    error_code=_http_error_code(exc.status_code),
                    category="http",
                    http_status=exc.status_code,
                )
            payload = error_response_payload(
                public_exc or ApplicationError("系统处理失败，请稍后重试。"),
                request_id=self.request.headers.get("X-Request-Id"),
                fallback_message="系统处理失败，请稍后重试。",
            )
            self.set_status(http_status_for(public_exc) if isinstance(public_exc, ApplicationError) else status_code)
            self.set_header("Content-Type", "application/json; charset=UTF-8")
            self.finish(json.dumps(payload, ensure_ascii=False))
            return
        super().write_error(status_code, **kwargs)

    def log_exception(self, typ, value, tb) -> None:
        if isinstance(value, (ApplicationError, web.HTTPError)):
            return
        super().log_exception(typ, value, tb)


class BusinessHandler(BaseHandler):
    require_identity = True
    require_policy_auth = True


class DevHandler(BaseHandler):
    pass


def _http_error_code(status_code: int) -> str:
    if status_code == 403:
        return ErrorCode.BASE_PERMISSION_DENIED
    if status_code == 404:
        return ErrorCode.BASE_RESOURCE_NOT_FOUND
    if status_code == 409:
        return ErrorCode.BASE_RESOURCE_CONFLICT
    if status_code == 501:
        return ErrorCode.BASE_CAPABILITY_UNSUPPORTED
    return ErrorCode.BASE_UNKNOWN
