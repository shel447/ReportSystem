from __future__ import annotations

from types import SimpleNamespace
import json

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
