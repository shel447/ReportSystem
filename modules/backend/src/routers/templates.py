from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote

from pydantic import BaseModel

from ..contexts.report.application.template_models import template_import_preview_to_dict, template_summary_to_dict
from ..contexts.report.domain.template_models import report_template_from_dict, report_template_to_dict
from ..shared.kernel.policy_auth import policy_auth
from ..web.base import BusinessHandler


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


class TemplatesHandler(BusinessHandler):
    @policy_auth(resource="template", action="list")
    async def get(self):
        def action():
            with self.container.report_service_scope() as service:
                return [template_summary_to_dict(item) for item in service.list_templates()]
        self.write_json(await self.run_blocking(action))

    @policy_auth(resource="template", action="create")
    async def post(self):
        data = self.parse_json(TemplateUpsertRequest)
        def action():
            with self.container.report_service_scope() as service:
                return report_template_to_dict(service.create_template(report_template_from_dict(data.model_dump())))
        self.write_json(await self.run_blocking(action))


class TemplateHandler(BusinessHandler):
    @policy_auth(resource="template", action="read")
    async def get(self, template_id: str):
        def action():
            with self.container.report_service_scope() as service:
                return report_template_to_dict(service.get_template(template_id))
        self.write_json(await self.run_blocking(action))

    @policy_auth(resource="template", action="update")
    async def put(self, template_id: str):
        data = self.parse_json(TemplateUpsertRequest)
        def action():
            with self.container.report_service_scope() as service:
                return report_template_to_dict(service.update_template(template_id, report_template_from_dict(data.model_dump())))
        self.write_json(await self.run_blocking(action))

    @policy_auth(resource="template", action="delete")
    async def delete(self, template_id: str):
        def action():
            with self.container.report_service_scope() as service:
                service.delete_template(template_id)
                return {"message": "deleted"}
        self.write_json(await self.run_blocking(action))


class TemplateImportPreviewHandler(BusinessHandler):
    @policy_auth(resource="template", action="import_preview")
    async def post(self):
        data = self.parse_json(TemplateImportPreviewRequest)
        def action():
            with self.container.report_service_scope() as service:
                return template_import_preview_to_dict(service.preview_import_template(data.content))
        self.write_json(await self.run_blocking(action))


class TemplateExportHandler(BusinessHandler):
    @policy_auth(resource="template", action="export")
    async def get(self, template_id: str):
        def action():
            with self.container.report_service_scope() as service:
                payload, filename = service.export_template(template_id)
                return report_template_to_dict(payload), filename
        payload, filename = await self.run_blocking(action)
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Content-Disposition", _build_download_header(filename))
        self.finish(json.dumps(payload, ensure_ascii=False, indent=2))


def _build_download_header(filename: str) -> str:
    fallback = re.sub(r"[^0-9A-Za-z._-]+", "-", filename).strip("-") or "template-export.json"
    return f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{quote(filename)}'


ROUTES = [
    (r"/rest/chatbi/v1/templates", TemplatesHandler),
    (r"/rest/chatbi/v1/templates/import/preview", TemplateImportPreviewHandler),
    (r"/rest/chatbi/v1/templates/([^/]+)/export", TemplateExportHandler),
    (r"/rest/chatbi/v1/templates/([^/]+)", TemplateHandler),
]
