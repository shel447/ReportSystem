from __future__ import annotations

from types import SimpleNamespace
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread

from requests import Session
from sqlalchemy import Column, String, inspect
from runtime.cache import zenith_instance
from runtime.client._session import GLOBAL_HTTP_SESSION, RuntimeSession
from runtime.config import Ini
from runtime.db import TableBase
from runtime.log import get_log, set_level
from runtime.schedule import Job, Schedule
from runtime.server import PythonRuntime, Route, create_application, router
from tornado.testing import AsyncHTTPTestCase


class RuntimeManagedRecord(TableBase):
    __tablename__ = "runtime_managed_records"

    id = Column(String, primary_key=True)


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


def test_runtime_ini_can_reload_an_explicit_file(tmp_path):
    path = tmp_path / "runtime.ini"
    path.write_text("[log]\nlevel = DEBUG\n", encoding="utf-8")
    ini = Ini()

    ini.load(path)

    assert ini.get("log", "level") == "DEBUG"


def test_runtime_table_base_and_named_database_instance(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNTIME_DB_DIR", str(tmp_path))
    instance_name = f"runtime_test_{tmp_path.name}"
    first = zenith_instance(instance_name)
    second = zenith_instance(instance_name)

    session_one = first.session()
    session_two = second.session()
    try:
        session_one.add(RuntimeManagedRecord(id="record_1"))
        session_one.commit()
        assert session_two.query(RuntimeManagedRecord).one().id == "record_1"
        assert "runtime_managed_records" in inspect(session_one.get_bind()).get_table_names()
    finally:
        session_one.close()
        session_two.close()

    assert first is second
    assert (tmp_path / f"{instance_name}.db").exists()


def test_runtime_business_instance_keeps_local_report_system_database_name(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNTIME_DB_DIR", str(tmp_path))

    session = zenith_instance("dtesmartbiservicedb").session()
    session.close()

    assert (tmp_path / "report_system.db").exists()


def test_runtime_log_returns_stable_minimal_logger_and_updates_level():
    first = get_log("runtime-test")
    second = get_log("runtime-test")

    set_level("DEBUG")

    assert first is second
    assert first.depth == 0
    assert not hasattr(first, "warning")
    assert all(hasattr(first, name) for name in ("debug", "info", "warn", "error", "critical", "exception"))
    assert first._logger.level == 10


def test_runtime_schedule_runs_one_time_job_with_params():
    received = []
    job = Job(lambda params: received.append(params), params={"id": "job_1"})

    should_repeat = job.run()

    assert received == [{"id": "job_1"}]
    assert should_repeat is False


def test_runtime_schedule_run_waits_for_delay_and_executes_one_time_job(monkeypatch):
    from runtime.schedule import _schedule as schedule_module

    executed = Event()
    sleeps = []
    monkeypatch.setattr(schedule_module.time, "sleep", lambda seconds: sleeps.append(seconds))
    schedule = Schedule()
    schedule.add(func=lambda _params: executed.set(), delay=2)

    Thread(target=schedule.run, daemon=True).start()

    assert executed.wait(timeout=1)
    assert sleeps == [2]
    assert schedule._jobs == []


def test_runtime_schedule_reschedules_interval_job():
    job = Job(lambda _params: None, interval=30)
    previous_next_time = job.next_time

    should_repeat = job.run()

    assert should_repeat is True
    assert job.next_time >= previous_next_time


def test_runtime_schedule_adds_jobs_and_rejects_invalid_inputs():
    schedule = Schedule()

    assert schedule.add(func=lambda _params: None, delay=2) is True
    assert schedule.add(func=None) is False
    assert schedule.add_job(None) is False
    assert len(schedule._jobs) == 1


def test_runtime_schedule_accepts_custom_job():
    class CustomJob:
        next_time = 0

        def run(self):
            return False

        def __lt__(self, other):
            return self.next_time < other.next_time

    schedule = Schedule()

    assert schedule.add_job(CustomJob()) is True
    assert len(schedule._jobs) == 1
