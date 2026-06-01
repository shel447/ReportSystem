import json
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.contexts.report.application.template_models import TemplateImportPreview
from src.contexts.report.domain.template_models import TemplateSummary, report_template_from_dict
from src.main import create_app
from src.routers.templates import (
    TemplateImportPreviewRequest,
    TemplateUpsertRequest,
    create_template,
    export_template_definition,
    list_templates,
    preview_import_template,
    update_template,
)
from src.shared.kernel.errors import ConflictError, NotFoundError, ValidationError
from tests.support.builders import load_json_fixture
from tests.support.paths import testdata_path as fixture_path


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
                TemplateSummary(
                    id="tpl_network_daily",
                    category="network_operations",
                    name="网络运行日报",
                    description="面向网络运维中心的统一日报模板。",
                    schema_version="template.v3",
                )
            ]
        )

        with patch("src.routers.templates.build_report_service", return_value=fake_service):
            payload = list_templates(db=object())

        self.assertEqual(payload[0]["id"], "tpl_network_daily")
        self.assertEqual(payload[0]["structureType"], "flow")
        self.assertNotIn("parameters", payload[0])
        self.assertNotIn("catalogs", payload[0])

    def test_create_template_accepts_formal_report_template(self):
        fake_service = SimpleNamespace(create_template=lambda payload: payload)

        with patch("src.routers.templates.build_report_service", return_value=fake_service):
            payload = create_template(TemplateUpsertRequest(**_sample_template()), db=object())

        self.assertEqual(payload["schemaVersion"], "template.v3")
        self.assertIn("catalogs", payload)
        self.assertNotIn("sections", payload)

    def test_create_template_accepts_paged_report_template(self):
        fake_service = SimpleNamespace(create_template=lambda payload: payload)
        paged_template = {
            **_sample_template(),
            "id": "tpl_network_ppt",
            "name": "网络运行 PPT 汇报",
            "structureType": "paged",
            "chapters": [
                {
                    "id": "chapter_overview",
                    "title": "整体概览",
                    "slides": [{"id": "slide_kpi", "title": "核心指标", "sections": []}],
                }
            ],
        }
        del paged_template["catalogs"]

        with patch("src.routers.templates.build_report_service", return_value=fake_service):
            payload = create_template(TemplateUpsertRequest(**paged_template), db=object())

        self.assertEqual(payload["structureType"], "paged")
        self.assertIn("chapters", payload)
        self.assertNotIn("catalogs", payload)

    def test_update_template_requires_same_path_and_body_id(self):
        fake_service = SimpleNamespace(
            update_template=lambda *_args, **_kwargs: (_ for _ in ()).throw(ValidationError("Template id mismatch"))
        )

        with patch("src.routers.templates.build_report_service", return_value=fake_service):
            with self.assertRaises(HTTPException) as ctx:
                update_template("tpl_a", TemplateUpsertRequest(**{**_sample_template(), "id": "tpl_b"}), db=object())

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Template id mismatch")

    def test_export_template_definition_returns_formal_template_json(self):
        template = report_template_from_dict(_sample_template())
        fake_service = SimpleNamespace(
            export_template=lambda template_id: (template, "网络运行日报-20260418-120000.json")
        )

        with patch("src.routers.templates.build_report_service", return_value=fake_service):
            response = export_template_definition("tpl_network_daily", db=object())

        self.assertEqual(response.media_type, "application/json")
        payload = json.loads(response.body.decode("utf-8"))
        self.assertEqual(payload["catalogs"][0]["id"], "catalog_overview")
        self.assertNotIn("sections", payload)

    def test_preview_import_template_uses_content_only(self):
        normalized = report_template_from_dict(_sample_template())
        fake_service = SimpleNamespace(
            preview_import_template=lambda raw_content: TemplateImportPreview(normalized_template=normalized, warnings=[])
        )

        with patch("src.routers.templates.build_report_service", return_value=fake_service):
            result = preview_import_template(
                TemplateImportPreviewRequest(content=normalized),
                db=object(),
            )

        self.assertEqual(result["normalizedTemplate"]["id"], "tpl_network_daily")
        self.assertEqual(result["warnings"], [])

    def test_preview_import_template_returns_structured_warnings(self):
        normalized = report_template_from_dict(_sample_template())
        fake_service = SimpleNamespace(
            preview_import_template=lambda raw_content: TemplateImportPreview(
                normalized_template=normalized,
                warnings=["已自动补齐缺省结构类型"],
            )
        )

        with patch("src.routers.templates.build_report_service", return_value=fake_service):
            result = preview_import_template(
                TemplateImportPreviewRequest(content=normalized),
                db=object(),
            )

        self.assertEqual(result["warnings"][0]["code"], "import_warning")
        self.assertEqual(result["warnings"][0]["message"], "已自动补齐缺省结构类型")

    def test_preview_import_template_validation_error_maps_to_http_400(self):
        fake_service = SimpleNamespace(
            preview_import_template=lambda *_args, **_kwargs: (_ for _ in ()).throw(ValidationError("Invalid template"))
        )

        with patch("src.routers.templates.build_report_service", return_value=fake_service):
            with self.assertRaises(HTTPException) as ctx:
                preview_import_template(TemplateImportPreviewRequest(content={"foo": "bar"}), db=object())

        self.assertEqual(ctx.exception.status_code, 400)

    def test_router_maps_conflict_and_not_found(self):
        fake_create = SimpleNamespace(
            create_template=lambda *_args, **_kwargs: (_ for _ in ()).throw(ConflictError("Template already exists"))
        )
        with patch("src.routers.templates.build_report_service", return_value=fake_create):
            with self.assertRaises(HTTPException) as create_ctx:
                create_template(TemplateUpsertRequest(**_sample_template()), db=object())
        self.assertEqual(create_ctx.exception.status_code, 409)

        fake_update = SimpleNamespace(
            update_template=lambda *_args, **_kwargs: (_ for _ in ()).throw(NotFoundError("Template not found"))
        )
        with patch("src.routers.templates.build_report_service", return_value=fake_update):
            with self.assertRaises(HTTPException) as update_ctx:
                update_template("tpl_network_daily", TemplateUpsertRequest(**_sample_template()), db=object())
        self.assertEqual(update_ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()


def test_testdata_templates_import_create_update_export_roundtrip(tmp_path):
    fixtures = sorted(fixture_path("report-templates").glob("*.json"))
    assert fixtures

    with TestClient(create_app(frontend_dir=str(tmp_path)), headers={"X-User-Id": "template-admin"}) as client:
        for fixture in fixtures:
            template = deepcopy(load_json_fixture("report-templates", fixture.name))
            template["id"] = f"tpl_roundtrip_{fixture.stem.replace('-', '_')}"
            structure_type = template.get("structureType") or "flow"

            preview = client.post("/rest/chatbi/v1/templates/import/preview", json={"content": template})
            assert preview.status_code == 200, preview.text
            preview_payload = preview.json()
            assert preview_payload["normalizedTemplate"]["id"] == template["id"]
            assert preview_payload["normalizedTemplate"]["structureType"] == structure_type
            assert all(isinstance(item, dict) and item.get("code") and item.get("message") is not None for item in preview_payload["warnings"])

            created = client.post("/rest/chatbi/v1/templates", json=preview_payload["normalizedTemplate"])
            assert created.status_code == 200, created.text
            created_payload = created.json()
            assert created_payload["structureType"] == structure_type
            if structure_type == "paged":
                assert "chapters" in created_payload
                assert "catalogs" not in created_payload
            else:
                assert "catalogs" in created_payload
                assert "chapters" not in created_payload

            listed = client.get("/rest/chatbi/v1/templates")
            assert listed.status_code == 200
            listed_item = next(item for item in listed.json() if item["id"] == template["id"])
            assert listed_item["structureType"] == structure_type

            detail = client.get(f"/rest/chatbi/v1/templates/{template['id']}")
            assert detail.status_code == 200
            assert detail.json()["structureType"] == structure_type

            updated_template = deepcopy(detail.json())
            updated_template["description"] = f"{updated_template['description']} roundtrip"
            updated = client.put(f"/rest/chatbi/v1/templates/{template['id']}", json=updated_template)
            assert updated.status_code == 200, updated.text
            assert updated.json()["structureType"] == structure_type

            exported = client.get(f"/rest/chatbi/v1/templates/{template['id']}/export")
            assert exported.status_code == 200
            assert exported.json()["structureType"] == structure_type

            deleted = client.delete(f"/rest/chatbi/v1/templates/{template['id']}")
            assert deleted.status_code == 200
