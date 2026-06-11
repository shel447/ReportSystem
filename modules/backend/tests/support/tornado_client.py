from __future__ import annotations

from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
import asyncio
import threading
from typing import Any

import httpx
from tornado import httpserver, ioloop, netutil
from runtime.server import create_application

from src.controllers import ChatController, HealthCheckController, ReportController, TemplateController


class TornadoTestClient:
    """Small synchronous client backed by a real Tornado HTTP server."""
    __test__ = False

    def __init__(self, app, *, headers: dict[str, str] | None = None) -> None:
        from src.infrastructure.persistence.database import init_db
        init_db()
        self.app = app
        self.default_headers = headers or {}
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=10):
            raise RuntimeError("Tornado test server did not start")
        self.client = httpx.Client(base_url=f"http://127.0.0.1:{self.port}", headers=self.default_headers)

    def _run(self) -> None:
        self.loop = ioloop.IOLoop()
        self.loop.make_current()
        sockets = netutil.bind_sockets(0, address="127.0.0.1")
        self.port = sockets[0].getsockname()[1]
        self.server = httpserver.HTTPServer(self.app)
        self.server.add_sockets(sockets)
        self._ready.set()
        self.loop.start()
        self.server.stop()
        self.loop.close(all_fds=True)

    def close(self) -> None:
        self.client.close()
        self.loop.add_callback(self.loop.stop)
        self._thread.join(timeout=10)
        server = self.app.settings.get("chatbi_server")
        if server is not None and hasattr(server, "destroy"):
            server.destroy()
        elif server is not None and hasattr(server, "close"):
            server.close()

    def __enter__(self) -> "TornadoTestClient":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def get(self, path: str, **kwargs):
        return self.client.get(path, **kwargs)

    def post(self, path: str, **kwargs):
        return self.client.post(path, **kwargs)

    def put(self, path: str, **kwargs):
        return self.client.put(path, **kwargs)

    def delete(self, path: str, **kwargs):
        return self.client.delete(path, **kwargs)


@contextmanager
def fixed_scope(value: Any):
    yield value


class FakeWebContainer:
    def __init__(self, *, report_service=None, conversation_service=None, policy_auth_gateway=None) -> None:
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.policy_auth_gateway = policy_auth_gateway
        self.audit_publisher = type("AuditPublisher", (), {"submit": lambda self, event: None})()
        self._report_service = report_service
        self._conversation_service = conversation_service

    @contextmanager
    def report_service_scope(self):
        yield self._report_service

    @contextmanager
    def conversation_service_scope(self):
        yield self._conversation_service

    def close(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)

    async def run_blocking(self, call, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, lambda: call(*args, **kwargs))


def create_app(*, frontend_dir=None, container=None):
    if container is None:
        from src.infrastructure.chatbi_server import ChatBIServer
        server = ChatBIServer()
        server.initialize()
    else:
        server = container
    app = create_application(
        [
            ChatController(server),
            TemplateController(server),
            ReportController(server),
            HealthCheckController(),
        ]
    )
    app.settings["chatbi_server"] = server
    return app
