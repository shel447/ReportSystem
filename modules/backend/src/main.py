"""Smart report system FastAPI entrypoint."""
from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .infrastructure.persistence.database import init_db
from .infrastructure.platform.runtime import build_policy_auth_gateway, start_platform_runtime, stop_platform_runtime
from .routers import chat, docs, feedback, reports, system_settings, templates
from .shared.kernel.errors import ApplicationError, ErrorCode, error_response_payload, http_status_for
from .shared.kernel.http import get_current_user_id
from .shared.kernel.paths import project_root
from .shared.kernel.policy_auth import enforce_policy_auth

CHATBI_PREFIX = "/rest/chatbi/v1"
DEV_PREFIX = "/rest/dev"
FRONTEND_DIST_DIR = str(project_root() / "modules" / "frontend" / "dist")


def create_app(*, frontend_dir: str | None = None) -> FastAPI:
    app = FastAPI(title="Smart Report System", version="1.6.0")
    app.state.policy_auth_gateway = build_policy_auth_gateway()
    register_error_handlers(app)

    business_dependencies = [Depends(get_current_user_id), Depends(enforce_policy_auth)]
    app.include_router(templates.router, prefix=CHATBI_PREFIX, dependencies=business_dependencies)
    app.include_router(chat.router, prefix=CHATBI_PREFIX, dependencies=business_dependencies)
    app.include_router(reports.router, prefix=CHATBI_PREFIX, dependencies=business_dependencies)

    app.include_router(docs.router, prefix=DEV_PREFIX)
    app.include_router(feedback.router, prefix=DEV_PREFIX)
    app.include_router(system_settings.router, prefix=DEV_PREFIX)

    resolved_frontend_dir = frontend_dir or FRONTEND_DIST_DIR
    assets_dir = os.path.join(resolved_frontend_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

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
        start_platform_runtime()
        print("Database initialized")
        print("Server startup complete")

    @app.on_event("shutdown")
    def on_shutdown() -> None:
        stop_platform_runtime()

    return app


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
        return JSONResponse(
            status_code=http_status_for(exc),
            content=error_response_payload(exc, request_id=request.headers.get("X-Request-Id")),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        if not _is_chatbi_business_path(request):
            return JSONResponse(status_code=422, content={"detail": exc.errors()})
        payload = error_response_payload(
            ApplicationError(
                "输入参数校验失败，请检查请求内容。",
                details={"errors": exc.errors()},
                error_code=ErrorCode.BASE_PARAM_INVALID,
                category="param",
                http_status=400,
            ),
            request_id=request.headers.get("X-Request-Id"),
        )
        return JSONResponse(status_code=400, content=payload)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        if not _is_chatbi_business_path(request):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        payload = error_response_payload(
            ApplicationError(
                str(exc.detail or "请求处理失败。"),
                error_code=_http_error_code(exc.status_code),
                category="http",
                http_status=exc.status_code,
            ),
            request_id=request.headers.get("X-Request-Id"),
        )
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(Exception)
    async def unknown_error_handler(request: Request, exc: Exception) -> JSONResponse:
        if not _is_chatbi_business_path(request):
            raise exc
        payload = error_response_payload(
            exc,
            request_id=request.headers.get("X-Request-Id"),
            fallback_message="系统处理失败，请稍后重试。",
        )
        return JSONResponse(status_code=500, content=payload)


def _is_chatbi_business_path(request: Request) -> bool:
    return request.url.path.startswith(CHATBI_PREFIX)


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

    uvicorn.run("src.main:app", host="0.0.0.0", port=8300, reload=True)
