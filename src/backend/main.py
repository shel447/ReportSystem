"""Smart report system FastAPI entrypoint."""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .infrastructure.persistence.database import init_db
from .routers import chat, design, documents, feedback, instances, system_settings, tasks, template_instances, templates

API_PREFIX = "/api"
BACKEND_DIR = os.path.dirname(__file__)
FRONTEND_SOURCE_DIR = os.path.join(BACKEND_DIR, "..", "frontend")
FRONTEND_DIST_DIR = os.path.join(FRONTEND_SOURCE_DIR, "dist")


def create_app(*, frontend_dir: str | None = None) -> FastAPI:
    app = FastAPI(title="Smart Report System", version="1.6.0")

    app.include_router(templates.router, prefix=API_PREFIX)
    app.include_router(template_instances.router, prefix=API_PREFIX)
    app.include_router(instances.router, prefix=API_PREFIX)
    app.include_router(documents.router, prefix=API_PREFIX)
    app.include_router(tasks.router, prefix=API_PREFIX)
    app.include_router(chat.router, prefix=API_PREFIX)
    app.include_router(design.router, prefix=API_PREFIX)
    app.include_router(feedback.router, prefix=API_PREFIX)
    app.include_router(system_settings.router, prefix=API_PREFIX)

    resolved_frontend_dir = frontend_dir or FRONTEND_DIST_DIR
    assets_dir = os.path.join(resolved_frontend_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    async def index() -> FileResponse:
        return _serve_frontend_file(resolved_frontend_dir, "")

    @app.get("/{full_path:path}")
    async def spa_entry(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        return _serve_frontend_file(resolved_frontend_dir, full_path)

    @app.on_event("startup")
    def on_startup() -> None:
        init_db()
        print("Database initialized")
        print("Server started: http://localhost:8000")

    return app


def _serve_frontend_file(frontend_dir: str, requested_path: str) -> FileResponse:
    index_path = os.path.join(frontend_dir, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Frontend build not found")

    requested_path = (requested_path or "").strip("/")
    if requested_path:
        frontend_root = os.path.abspath(frontend_dir)
        candidate = os.path.abspath(os.path.join(frontend_root, requested_path))
        if candidate.startswith(frontend_root) and os.path.isfile(candidate):
            return FileResponse(candidate, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

    return FileResponse(index_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.backend.main:app", host="0.0.0.0", port=8000, reload=True)
