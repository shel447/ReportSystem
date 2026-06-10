from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote

from pydantic import BaseModel
from runtime.server import router
from tornado.web import RequestHandler

from ..contexts.report.application.template_models import template_import_preview_to_dict, template_summary_to_dict
from ..contexts.report.domain.template_models import report_template_from_dict, report_template_to_dict
from ..shared.kernel.authenticated import authenticated
from .common import parse_body, required_query

PRIVILEGE = ["dte.bi.chat.edit"]


class TemplateUpsertRequest(BaseModel):
    id: str
    category: str
    name: str
    description: str
    schemaVersion: str
    structureType: str | None = None
    parameters: list[dict[str, Any]]
    catalogs: list[dict[str, Any]] | None = None
    chapters: list[dict[str, Any]] | None = None


class TemplateImportPreviewRequest(BaseModel):
    content: Any


class TemplateController:
    def __init__(self, server) -> None:
        self.server = server

    @router.GET("/rest/chatbi/v1/templates", user_handler=True)
    @authenticated(origin_url="/rest/chatbi/v1/templates", privilege=PRIVILEGE)
    async def list_templates(self, req: RequestHandler, **query):
        def action():
            with self.server.report_service_scope() as service:
                return [template_summary_to_dict(item) for item in service.list_templates()]
        return await self.server.run_blocking(action)

    @router.POST("/rest/chatbi/v1/templates", user_handler=True, use_body=True)
    @authenticated(origin_url="/rest/chatbi/v1/templates", privilege=PRIVILEGE)
    async def create_template(self, req: RequestHandler, body, **query):
        data = parse_body(body, TemplateUpsertRequest)
        def action():
            with self.server.report_service_scope() as service:
                return report_template_to_dict(service.create_template(report_template_from_dict(data.model_dump())))
        return await self.server.run_blocking(action)

    @router.GET("/rest/chatbi/v1/templates/detail", user_handler=True)
    @authenticated(origin_url="/rest/chatbi/v1/templates/detail", privilege=PRIVILEGE)
    async def get_template(self, req: RequestHandler, **query):
        template_id = required_query(req, query, "templateId")
        def action():
            with self.server.report_service_scope() as service:
                return report_template_to_dict(service.get_template(template_id))
        return await self.server.run_blocking(action)

    @router.PUT("/rest/chatbi/v1/templates/detail", user_handler=True, use_body=True)
    @authenticated(origin_url="/rest/chatbi/v1/templates/detail", privilege=PRIVILEGE)
    async def update_template(self, req: RequestHandler, body, **query):
        template_id = required_query(req, query, "templateId")
        data = parse_body(body, TemplateUpsertRequest)
        def action():
            with self.server.report_service_scope() as service:
                return report_template_to_dict(service.update_template(template_id, report_template_from_dict(data.model_dump())))
        return await self.server.run_blocking(action)

    @router.DELETE("/rest/chatbi/v1/templates/detail", user_handler=True)
    @authenticated(origin_url="/rest/chatbi/v1/templates/detail", privilege=PRIVILEGE)
    async def delete_template(self, req: RequestHandler, **query):
        template_id = required_query(req, query, "templateId")
        def action():
            with self.server.report_service_scope() as service:
                service.delete_template(template_id)
                return {"message": "deleted"}
        return await self.server.run_blocking(action)

    @router.POST("/rest/chatbi/v1/templates/import/preview", user_handler=True, use_body=True)
    @authenticated(origin_url="/rest/chatbi/v1/templates/import/preview", privilege=PRIVILEGE)
    async def preview_import(self, req: RequestHandler, body, **query):
        data = parse_body(body, TemplateImportPreviewRequest)
        def action():
            with self.server.report_service_scope() as service:
                return template_import_preview_to_dict(service.preview_import_template(data.content))
        return await self.server.run_blocking(action)

    @router.GET("/rest/chatbi/v1/templates/export", user_handler=True)
    @authenticated(origin_url="/rest/chatbi/v1/templates/export", privilege=PRIVILEGE)
    async def export_template(self, req: RequestHandler, **query):
        template_id = required_query(req, query, "templateId")
        def action():
            with self.server.report_service_scope() as service:
                payload, filename = service.export_template(template_id)
                return report_template_to_dict(payload), filename
        payload, filename = await self.server.run_blocking(action)
        req.set_header("Content-Type", "application/json; charset=UTF-8")
        req.set_header("Content-Disposition", _build_download_header(filename))
        req.finish(json.dumps(payload, ensure_ascii=False, indent=2))


def _build_download_header(filename: str) -> str:
    fallback = re.sub(r"[^0-9A-Za-z._-]+", "-", filename).strip("-") or "template-export.json"
    return f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{quote(filename)}'
