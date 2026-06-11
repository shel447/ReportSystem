from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

from src.contexts.report.application.template_models import TemplateImportPreview
from src.contexts.report.domain.template_models import TemplateSummary, report_template_from_dict
from tests.support.tornado_client import create_app
from tests.support.builders import load_json_fixture
from tests.support.paths import testdata_path as fixture_path
from tests.support.tornado_client import FakeWebContainer, TornadoTestClient


def _template():
    return load_json_fixture("report-templates", "network-daily-flow.json")


def test_template_handlers_use_report_service_scope(tmp_path):
    template = report_template_from_dict(_template())
    service = SimpleNamespace(
        list_templates=lambda: [TemplateSummary(id=template.id, category=template.category, name=template.name, description=template.description, schema_version=template.schema_version)],
        get_template=lambda _id: template,
        create_template=lambda payload: payload,
        update_template=lambda _id, payload: payload,
        delete_template=lambda _id: None,
        preview_import_template=lambda content: TemplateImportPreview(normalized_template=report_template_from_dict(content), warnings=[]),
        export_template=lambda _id: (template, "template.json"),
    )
    with TornadoTestClient(create_app(frontend_dir=str(tmp_path), container=FakeWebContainer(report_service=service)), headers={"X-User-Id": "user"}) as client:
        assert client.get("/rest/chatbi/v1/templates").json()[0]["structureType"] == "flow"
        assert client.post("/rest/chatbi/v1/templates/import/preview", json={"content": _template()}).status_code == 200
        assert client.get("/rest/chatbi/v1/templates/export", params={"templateId": template.id}).json()["id"] == template.id


def test_testdata_templates_import_create_update_export_roundtrip(tmp_path):
    fixtures = sorted(fixture_path("report-templates").glob("*.json"))
    with TornadoTestClient(create_app(frontend_dir=str(tmp_path)), headers={"X-User-Id": "template-admin"}) as client:
        for fixture in fixtures:
            template = deepcopy(load_json_fixture("report-templates", fixture.name))
            template["id"] = f"tpl_roundtrip_{fixture.stem.replace('-', '_')}"
            preview = client.post("/rest/chatbi/v1/templates/import/preview", json={"content": template})
            assert preview.status_code == 200, preview.text
            created = client.post("/rest/chatbi/v1/templates", json=preview.json()["normalizedTemplate"])
            assert created.status_code == 200, created.text
            assert client.get("/rest/chatbi/v1/templates/detail", params={"templateId": template["id"]}).status_code == 200
            updated = deepcopy(created.json())
            updated["description"] += " updated"
            assert client.put("/rest/chatbi/v1/templates/detail", params={"templateId": template["id"]}, json=updated).status_code == 200
            assert client.get("/rest/chatbi/v1/templates/export", params={"templateId": template["id"]}).status_code == 200
            assert client.delete("/rest/chatbi/v1/templates/detail", params={"templateId": template["id"]}).status_code == 200


def test_template_query_parameters_are_required_and_legacy_paths_are_removed(tmp_path):
    with TornadoTestClient(create_app(frontend_dir=str(tmp_path)), headers={"X-User-Id": "template-admin"}) as client:
        missing = client.get("/rest/chatbi/v1/templates/detail")
        duplicate = client.get("/rest/chatbi/v1/templates/detail?templateId=one&templateId=two")
        legacy = client.get("/rest/chatbi/v1/templates/legacy-template")
    assert missing.status_code == 400
    assert missing.json()["errorCode"] == "chatbi.base.param.invalid"
    assert duplicate.status_code == 400
    assert duplicate.json()["errorCode"] == "chatbi.base.param.invalid"
    assert legacy.status_code == 404
