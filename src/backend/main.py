"""Smart report system FastAPI entrypoint."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .infrastructure.persistence.database import SessionLocal, init_db
from .infrastructure.persistence.models import User
from .routers import chat, design, feedback, parameter_options, reports, system_settings, templates
from .shared.kernel.http import resolve_user_id

CHATBI_PREFIX = "/rest/chatbi/v1"
DEV_PREFIX = "/rest/dev"
BACKEND_DIR = os.path.dirname(__file__)
FRONTEND_SOURCE_DIR = os.path.join(BACKEND_DIR, "..", "frontend")
FRONTEND_DIST_DIR = os.path.join(FRONTEND_SOURCE_DIR, "dist")


def create_app(*, frontend_dir: str | None = None) -> FastAPI:
    app = FastAPI(title="Smart Report System", version="1.6.0")

    app.include_router(templates.router, prefix=CHATBI_PREFIX)
    app.include_router(chat.router, prefix=CHATBI_PREFIX)
    app.include_router(parameter_options.router, prefix=CHATBI_PREFIX)
    app.include_router(reports.router, prefix=CHATBI_PREFIX)

    app.include_router(design.router, prefix=DEV_PREFIX)
    app.include_router(feedback.router, prefix=DEV_PREFIX)
    app.include_router(system_settings.router, prefix=DEV_PREFIX)

    resolved_frontend_dir = frontend_dir or FRONTEND_DIST_DIR
    assets_dir = os.path.join(resolved_frontend_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.middleware("http")
    async def ensure_chatbi_user(request: Request, call_next):
        if request.url.path.startswith(CHATBI_PREFIX):
            user_id = resolve_user_id(request.headers.get("X-User-Id"))
            db = SessionLocal()
            try:
                User.__table__.create(bind=db.get_bind(), checkfirst=True)
                row = db.query(User).filter(User.id == user_id).first()
                if row is None:
                    row = User(id=user_id, display_name=user_id, status="active", profile_json={})
                    db.add(row)
                row.last_seen_at = datetime.now(timezone.utc).replace(microsecond=0)
                db.commit()
            finally:
                db.close()
        return await call_next(request)

    @app.get("/")
    async def index() -> FileResponse:
        return _serve_frontend_file(resolved_frontend_dir, "")

    @app.get("/{full_path:path}")
    async def spa_entry(full_path: str) -> FileResponse:
        if full_path.startswith("api/") or full_path.startswith("rest/"):
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
