from __future__ import annotations

import copy

from fastapi.testclient import TestClient

from src.main import create_app
from tests.support.builders import load_json_fixture


def test_template_management_api_crud_import_preview_and_export(tmp_path):
    template = load_json_fixture("report-templates", "network-daily-flow.json")
    template["id"] = "tpl_e2e_network_daily"
    with TestClient(create_app(frontend_dir=str(tmp_path)), headers={"X-User-Id": "template-admin"}) as client:
        created = client.post("/rest/chatbi/v1/templates", json=template)
        assert created.status_code == 200

        listed = client.get("/rest/chatbi/v1/templates")
        assert listed.status_code == 200
        assert any(item["id"] == template["id"] for item in listed.json())

        detail = client.get(f"/rest/chatbi/v1/templates/{template['id']}")
        assert detail.status_code == 200
        assert detail.json()["name"] == template["name"]

        updated_template = copy.deepcopy(template)
        updated_template["description"] = "E2E 更新后的模板说明"
        updated = client.put(f"/rest/chatbi/v1/templates/{template['id']}", json=updated_template)
        assert updated.status_code == 200
        assert updated.json()["description"] == "E2E 更新后的模板说明"

        preview = client.post("/rest/chatbi/v1/templates/import/preview", json={"content": updated_template})
        assert preview.status_code == 200
        assert preview.json()["normalizedTemplate"]["id"] == template["id"]

        exported = client.get(f"/rest/chatbi/v1/templates/{template['id']}/export")
        assert exported.status_code == 200
        assert exported.json()["id"] == template["id"]

        deleted = client.delete(f"/rest/chatbi/v1/templates/{template['id']}")
        assert deleted.status_code == 200
        assert client.get(f"/rest/chatbi/v1/templates/{template['id']}").status_code == 404


def test_shared_template_is_visible_to_different_authenticated_users(tmp_path):
    template = load_json_fixture("report-templates", "network-daily-flow.json")
    template["id"] = "tpl_shared_network_daily"
    with TestClient(create_app(frontend_dir=str(tmp_path))) as client:
        created = client.post("/rest/chatbi/v1/templates", headers={"X-User-Id": "template-admin"}, json=template)
        assert created.status_code == 200

        detail = client.get(f"/rest/chatbi/v1/templates/{template['id']}", headers={"X-User-Id": "report-user"})
        assert detail.status_code == 200
        assert detail.json()["id"] == template["id"]
