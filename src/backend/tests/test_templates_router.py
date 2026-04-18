import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from backend.routers.templates import (
    TemplateImportPreviewRequest,
    TemplateUpsertRequest,
    create_template,
    export_template_definition,
    list_templates,
    preview_import_template,
    update_template,
)
from backend.shared.kernel.errors import ConflictError, NotFoundError, ValidationError


def _sample_template():
    return {
        "id": "tpl_network_daily",
        "category": "network_operations",
        "name": "网络运行日报",
        "description": "面向网络运维中心的统一日报模板。",
        "schemaVersion": "template.v3",
        "parameters": [],
        "catalogs": [
            {
                "id": "catalog_overview",
                "title": "运行概览",
                "sections": [],
            }
        ],
    }


class TemplatesRouterTests(unittest.TestCase):
    def test_list_templates_returns_template_summary_only(self):
        fake_service = SimpleNamespace(
            list_templates=lambda: [
                {
                    "id": "tpl_network_daily",
                    "category": "network_operations",
                    "name": "网络运行日报",
                    "description": "面向网络运维中心的统一日报模板。",
                    "schemaVersion": "template.v3",
                    "updatedAt": "2026-04-18T09:00:00Z",
                }
            ]
        )

        with patch("backend.routers.templates.build_template_catalog_service", return_value=fake_service):
            payload = list_templates(db=object())

        self.assertEqual(payload[0]["id"], "tpl_network_daily")
        self.assertNotIn("parameters", payload[0])
        self.assertNotIn("catalogs", payload[0])

    def test_create_template_accepts_formal_report_template(self):
        fake_service = SimpleNamespace(create_template=lambda payload: payload)

        with patch("backend.routers.templates.build_template_catalog_service", return_value=fake_service):
            payload = create_template(TemplateUpsertRequest(**_sample_template()), db=object())

        self.assertEqual(payload["schemaVersion"], "template.v3")
        self.assertIn("catalogs", payload)
        self.assertNotIn("sections", payload)

    def test_update_template_requires_same_path_and_body_id(self):
        fake_service = SimpleNamespace(
            update_template=lambda *_args, **_kwargs: (_ for _ in ()).throw(ValidationError("Template id mismatch"))
        )

        with patch("backend.routers.templates.build_template_catalog_service", return_value=fake_service):
            with self.assertRaises(HTTPException) as ctx:
                update_template("tpl_a", TemplateUpsertRequest(**{**_sample_template(), "id": "tpl_b"}), db=object())

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Template id mismatch")

    def test_export_template_definition_returns_formal_template_json(self):
        template = _sample_template()
        fake_service = SimpleNamespace(
            export_template=lambda template_id: (template, "网络运行日报-20260418-120000.json")
        )

        with patch("backend.routers.templates.build_template_catalog_service", return_value=fake_service):
            response = export_template_definition("tpl_network_daily", db=object())

        self.assertEqual(response.media_type, "application/json")
        payload = json.loads(response.body.decode("utf-8"))
        self.assertEqual(payload["catalogs"][0]["id"], "catalog_overview")
        self.assertNotIn("sections", payload)

    def test_preview_import_template_uses_content_only(self):
        normalized = _sample_template()
        fake_service = SimpleNamespace(
            preview_import_template=lambda raw_content: {
                "normalizedTemplate": normalized,
                "warnings": [],
            }
        )

        with patch("backend.routers.templates.build_template_catalog_service", return_value=fake_service):
            result = preview_import_template(
                TemplateImportPreviewRequest(content=normalized),
                db=object(),
            )

        self.assertEqual(result["normalizedTemplate"]["id"], "tpl_network_daily")

    def test_preview_import_template_validation_error_maps_to_http_400(self):
        fake_service = SimpleNamespace(
            preview_import_template=lambda *_args, **_kwargs: (_ for _ in ()).throw(ValidationError("Invalid template"))
        )

        with patch("backend.routers.templates.build_template_catalog_service", return_value=fake_service):
            with self.assertRaises(HTTPException) as ctx:
                preview_import_template(TemplateImportPreviewRequest(content={"foo": "bar"}), db=object())

        self.assertEqual(ctx.exception.status_code, 400)

    def test_router_maps_conflict_and_not_found(self):
        fake_create = SimpleNamespace(
            create_template=lambda *_args, **_kwargs: (_ for _ in ()).throw(ConflictError("Template already exists"))
        )
        with patch("backend.routers.templates.build_template_catalog_service", return_value=fake_create):
            with self.assertRaises(HTTPException) as create_ctx:
                create_template(TemplateUpsertRequest(**_sample_template()), db=object())
        self.assertEqual(create_ctx.exception.status_code, 409)

        fake_update = SimpleNamespace(
            update_template=lambda *_args, **_kwargs: (_ for _ in ()).throw(NotFoundError("Template not found"))
        )
        with patch("backend.routers.templates.build_template_catalog_service", return_value=fake_update):
            with self.assertRaises(HTTPException) as update_ctx:
                update_template("tpl_network_daily", TemplateUpsertRequest(**_sample_template()), db=object())
        self.assertEqual(update_ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
