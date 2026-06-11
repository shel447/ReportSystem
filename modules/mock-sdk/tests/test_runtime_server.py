from __future__ import annotations

from types import SimpleNamespace
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from requests import Session
from runtime.client._session import GLOBAL_HTTP_SESSION, RuntimeSession
from runtime.config import Ini
from runtime.server import PythonRuntime, Route, create_application, router
from tornado.testing import AsyncHTTPTestCase


class Controller:
    @router.POST("/items/{item_id}", user_handler=True, use_body=True)
    def update(self, req, body, **query):
        return {
            "itemId": req.path_params["item_id"],
            "userId": req.current_user_id,
            "body": body,
            "query": query,
        }


def test_router_annotation_records_route_definition():
    route = getattr(Controller().update, "__runtime_route__")
    assert route == Route(method="POST", path="/items/{item_id}", user_handler=True, use_body=True)


def test_python_runtime_calls_backend_lifecycle():
    calls = []
    module = SimpleNamespace(
        register_initialize=lambda: calls.append("initialize"),
        register_handler=lambda: calls.append("handler") or [Controller()],
        register_destroy=lambda: calls.append("destroy"),
    )
    runtime = PythonRuntime(module)

    app = runtime.initialize()
    runtime.destroy()

    assert app is not None
    assert calls == ["initialize", "handler", "destroy"]


def test_create_application_rejects_duplicate_routes():
    class Duplicate:
        @router.POST("/items/{item_id}")
        def update(self, req, **query):
            return {}

    try:
        create_application([Controller(), Duplicate()])
    except RuntimeError as exc:
        assert "duplicate runtime route" in str(exc)
    else:
        raise AssertionError("duplicate route was accepted")


class RuntimeHttpTests(AsyncHTTPTestCase):
    def get_app(self):
        return create_application([Controller()])

    def test_body_query_path_and_user_projection(self):
        response = self.fetch(
            "/items/item_1?view=detail",
            method="POST",
            headers={"Content-Type": "application/json", "X-User-Id": "user_1"},
            body=json.dumps({"name": "demo"}),
        )
        assert response.code == 200
        assert json.loads(response.body) == {
            "itemId": "item_1",
            "userId": "user_1",
            "body": {"name": "demo"},
            "query": {"view": "detail"},
        }


def test_runtime_session_is_shared_requests_session_and_resolves_relative_url(monkeypatch):
    monkeypatch.setenv("RUNTIME_CLIENT_BASE_URL", "http://runtime.example/base")

    prepared = RuntimeSession().prepare_request(__import__("requests").Request("GET", "/rest/demo"))

    assert isinstance(GLOBAL_HTTP_SESSION, Session)
    assert prepared.url == "http://runtime.example/base/rest/demo"


def test_runtime_session_streams_and_closes_response(monkeypatch):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"first")
            self.wfile.flush()
            self.wfile.write(b"second")

        def log_message(self, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("RUNTIME_CLIENT_BASE_URL", f"http://127.0.0.1:{server.server_port}")
    response = GLOBAL_HTTP_SESSION.post(url="/stream", stream=True)
    try:
        assert b"".join(response.iter_content(chunk_size=5)) == b"firstsecond"
    finally:
        response.close()
        server.shutdown()
        server.server_close()
    assert response.raw.closed is True


def test_runtime_ini_reads_configured_file(tmp_path, monkeypatch):
    path = tmp_path / "runtime.ini"
    path.write_text("[chatbi.data_analysis]\nquery_strategy = ibis_planner\n", encoding="utf-8")
    monkeypatch.setenv("RUNTIME_CONFIG_FILE", str(path))

    ini = Ini()

    assert ini.get("chatbi.data_analysis", "query_strategy") == "ibis_planner"
