"""Smart report system Tornado entrypoint."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from tornado import httpserver, ioloop, web

from .infrastructure.persistence.database import init_db
from .infrastructure.platform.runtime import start_platform_runtime, stop_platform_runtime
from .routers import chat, docs, feedback, reports, system_settings, templates
from .shared.kernel.paths import project_root
from .web.base import BaseHandler, DevHandler
from .web.container import WebContainer

CHATBI_PREFIX = "/rest/chatbi/v1"
DEV_PREFIX = "/rest/dev"
FRONTEND_DIST_DIR = str(project_root() / "modules" / "frontend" / "dist")


class OpenApiHandler(DevHandler):
    async def get(self):
        paths: dict[str, dict] = {}
        for pattern, handler in BUSINESS_ROUTES:
            path = _openapi_path(pattern)
            operations = paths.setdefault(path, {})
            for method in ("get", "post", "put", "delete"):
                endpoint = handler.__dict__.get(method)
                if endpoint is None:
                    continue
                operations[method] = {"operationId": f"{handler.__name__}.{method}", "responses": {"200": {"description": "Success"}}}
        self.write_json({"openapi": "3.1.0", "info": {"title": "Smart Report System", "version": "1.6.0"}, "paths": paths})


class FrontendHandler(BaseHandler):
    async def get(self, requested_path: str = ""):
        if requested_path.startswith(("api/", "rest/")):
            raise web.HTTPError(404, reason="Not found")
        frontend_dir = Path(self.application.settings["frontend_dir"]).resolve()
        index_path = frontend_dir / "index.html"
        if not index_path.is_file():
            raise web.HTTPError(404, reason="Frontend build not found")
        requested_path = (requested_path or "").strip("/")
        if requested_path:
            candidate = (frontend_dir / requested_path).resolve()
            if candidate.is_relative_to(frontend_dir) and candidate.is_file():
                self.set_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.finish(candidate.read_bytes())
                return
        self.set_header("Content-Type", "text/html; charset=UTF-8")
        self.set_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.finish(index_path.read_bytes())


BUSINESS_ROUTES = [*templates.ROUTES, *chat.ROUTES, *reports.ROUTES]
DEV_ROUTES = [*docs.ROUTES, *feedback.ROUTES, *system_settings.ROUTES]


def create_app(*, frontend_dir: str | None = None, container: WebContainer | None = None) -> web.Application:
    container = container or WebContainer()
    routes = [
        *[(pattern, handler, {"container": container}) for pattern, handler in BUSINESS_ROUTES],
        *[(pattern, handler, {"container": container}) for pattern, handler in DEV_ROUTES],
        (r"/openapi\.json", OpenApiHandler, {"container": container}),
        (r"/", FrontendHandler, {"container": container}),
        (r"/(.*)", FrontendHandler, {"container": container}),
    ]
    return web.Application(
        routes,
        container=container,
        frontend_dir=frontend_dir or FRONTEND_DIST_DIR,
        debug=False,
    )


def run_server(*, host: str = "0.0.0.0", port: int = 8300) -> None:
    init_db()
    start_platform_runtime()
    app = create_app()
    server = httpserver.HTTPServer(app)
    server.listen(port, address=host)
    print(f"ReportSystem Tornado server listening on http://{host}:{port}")
    try:
        ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
        stop_platform_runtime()
        app.settings["container"].close()


def _openapi_path(pattern: str) -> str:
    known = {
        r"/rest/chatbi/v1/templates/([^/]+)/export": "/rest/chatbi/v1/templates/{templateId}/export",
        r"/rest/chatbi/v1/templates/([^/]+)": "/rest/chatbi/v1/templates/{templateId}",
        r"/rest/chatbi/v1/chat/([^/]+)/stop": "/rest/chatbi/v1/chat/{chatId}/stop",
        r"/rest/chatbi/v1/chat/([^/]+)": "/rest/chatbi/v1/chat/{conversationId}",
        r"/rest/chatbi/v1/reports/([^/]+)/document-generations": "/rest/chatbi/v1/reports/{reportId}/document-generations",
        r"/rest/chatbi/v1/reports/([^/]+)/documents/([^/]+)/download": "/rest/chatbi/v1/reports/{reportId}/documents/{documentId}/download",
        r"/rest/chatbi/v1/reports/([^/]+)": "/rest/chatbi/v1/reports/{reportId}",
    }
    if pattern in known:
        return known[pattern]
    value = pattern.replace(r"\.", ".")
    index = 0
    while "([^/]+)" in value:
        value = value.replace("([^/]+)", f"{{param{index}}}", 1)
        index += 1
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.getenv("REPORT_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("REPORT_PORT", "8300")))
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
