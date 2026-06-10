"""Annotation-driven controller runtime backed by Tornado.

ReportSystem depends on this public surface. The Tornado application and server
assembly remain private to the runtime implementation.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
import importlib
import inspect
import json
import os
import re
from types import ModuleType
from typing import Any, Callable, Iterable

from tornado import httpserver, ioloop, web
from tornado.iostream import StreamClosedError


ROUTE_ATTR = "__runtime_route__"


@dataclass(frozen=True, slots=True)
class Route:
    method: str
    path: str
    user_handler: bool = False
    use_body: bool = False


class _Router:
    def GET(self, path: str, *, user_handler: bool = False, use_body: bool = False):
        return self._route("GET", path, user_handler=user_handler, use_body=use_body)

    def POST(self, path: str, *, user_handler: bool = False, use_body: bool = False):
        return self._route("POST", path, user_handler=user_handler, use_body=use_body)

    def PUT(self, path: str, *, user_handler: bool = False, use_body: bool = False):
        return self._route("PUT", path, user_handler=user_handler, use_body=use_body)

    def DELETE(self, path: str, *, user_handler: bool = False, use_body: bool = False):
        return self._route("DELETE", path, user_handler=user_handler, use_body=use_body)

    def _route(self, method: str, path: str, *, user_handler: bool, use_body: bool):
        route = Route(method=method, path=path, user_handler=user_handler, use_body=use_body)

        def decorator(func):
            setattr(func, ROUTE_ATTR, route)
            return func

        return decorator


router = _Router()


class _ControllerRequestHandler(web.RequestHandler):
    def initialize(self, *, endpoints: dict[str, tuple[Callable[..., Any], Route]]) -> None:
        self.endpoints = endpoints
        self.endpoint, self.route = endpoints.get(self.request.method, (None, None))
        self.current_user_id: str | None = None
        self.path_params: dict[str, str] = {}

    async def _execute_endpoint(self, **path_params: str) -> None:
        if self.endpoint is None or self.route is None:
            raise web.HTTPError(405, reason="method not allowed")
        self.path_params = dict(path_params)
        if self.route.user_handler:
            self.current_user_id = _resolve_user_id(self)
        query = {name: values[-1].decode("utf-8") for name, values in self.request.query_arguments.items() if values}
        args: list[Any] = [self]
        if self.route.use_body:
            args.append(_json_body(self))
        result = self.endpoint(*args, **query)
        if inspect.isawaitable(result):
            result = await result
        if self._finished or result is None:
            return
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.finish(json.dumps(result, ensure_ascii=False))

    async def get(self, **path_params: str) -> None:
        await self._execute_endpoint(**path_params)

    async def post(self, **path_params: str) -> None:
        await self._execute_endpoint(**path_params)

    async def put(self, **path_params: str) -> None:
        await self._execute_endpoint(**path_params)

    async def delete(self, **path_params: str) -> None:
        await self._execute_endpoint(**path_params)

    def write_error(self, status_code: int, **kwargs) -> None:
        exc_info = kwargs.get("exc_info")
        exc = exc_info[1] if exc_info else None
        payload = _error_payload(exc, request_id=self.request.headers.get("X-Request-Id"))
        status = int(getattr(exc, "http_status", status_code) or status_code)
        self.set_status(status)
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.finish(json.dumps(payload, ensure_ascii=False))


def create_application(controllers: Iterable[object]) -> web.Application:
    registered: dict[str, dict[str, tuple[Callable[..., Any], Route]]] = {}
    seen: set[tuple[str, str]] = set()
    for controller in controllers:
        for _, endpoint in inspect.getmembers(controller, predicate=callable):
            definition = getattr(endpoint, ROUTE_ATTR, None)
            if definition is None:
                continue
            key = (definition.method, definition.path)
            if key in seen:
                raise RuntimeError(f"duplicate runtime route: {definition.method} {definition.path}")
            seen.add(key)
            registered.setdefault(definition.path, {})[definition.method] = (endpoint, definition)
    routes = [
        (_tornado_pattern(path), _ControllerRequestHandler, {"endpoints": endpoints})
        for path, endpoints in sorted(registered.items(), key=lambda item: _route_priority(item[0]))
    ]
    return web.Application(routes, debug=False)


class PythonRuntime:
    def __init__(self, module: str | ModuleType, *, host: str = "0.0.0.0", port: int = 8300) -> None:
        self.module = importlib.import_module(module) if isinstance(module, str) else module
        self.host = host
        self.port = port
        self.application: web.Application | None = None
        self.server: httpserver.HTTPServer | None = None

    def initialize(self) -> web.Application:
        self.module.register_initialize()
        self.application = create_application(self.module.register_handler())
        return self.application

    def destroy(self) -> None:
        self.module.register_destroy()

    def run(self) -> None:
        initialized = False
        try:
            application = self.initialize()
            initialized = True
            self.server = httpserver.HTTPServer(application)
            self.server.listen(self.port, address=self.host)
            print(f"Python runtime listening on http://{self.host}:{self.port}")
            ioloop.IOLoop.current().start()
        except KeyboardInterrupt:
            pass
        finally:
            if self.server is not None:
                self.server.stop()
            if initialized:
                self.destroy()


def _tornado_pattern(path: str) -> str:
    pattern = re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", r"(?P<\1>[^/]+)", path)
    return f"{pattern}/?" if not pattern.endswith("/") else pattern


def _route_priority(path: str) -> tuple[int, int, str]:
    return (path.count("{"), -len(path), path)


def _json_body(handler: web.RequestHandler) -> Any:
    try:
        return json.loads(handler.request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise web.HTTPError(400, reason="invalid json body") from exc


def _resolve_user_id(handler: web.RequestHandler) -> str | None:
    value = str(handler.request.headers.get("X-User-Id") or os.getenv("REPORT_DEV_USER_ID") or "").strip()
    return value or None


def _error_payload(exc: Exception | None, *, request_id: str | None) -> dict[str, Any]:
    if exc is not None and hasattr(exc, "error_code"):
        payload = {
            "errorCode": getattr(exc, "error_code"),
            "errorMsg": getattr(exc, "message", str(exc)),
            "category": getattr(exc, "category", "business"),
            "retryable": bool(getattr(exc, "retryable", False)),
            "source": getattr(exc, "source", None),
            "requestId": request_id,
            "details": dict(getattr(exc, "details", {}) or {}),
        }
        return {key: value for key, value in payload.items() if value is not None}
    if isinstance(exc, web.HTTPError):
        return {"errorCode": "runtime.http.error", "errorMsg": exc.reason, "requestId": request_id}
    return {"errorCode": "runtime.unknown", "errorMsg": "request failed", "requestId": request_id}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default=os.getenv("RUNTIME_MODULE", "src"))
    parser.add_argument("--host", default=os.getenv("REPORT_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("REPORT_PORT", "8300")))
    args = parser.parse_args()
    PythonRuntime(args.module, host=args.host, port=args.port).run()


if __name__ == "__main__":
    main()
