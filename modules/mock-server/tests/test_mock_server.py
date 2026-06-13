import json

from fastapi.testclient import TestClient

from mock_server.main import create_app


client = TestClient(create_app())


def test_health_and_ai_protocols():
    assert client.get("/health").json() == {"status": "ok"}
    completion = client.post("/v1/chat/completions", json={"model": "mock", "messages": []}).json()
    assert completion["choices"][0]["message"]["content"] == "completion test ok"
    assert len(client.post("/v1/embeddings", json={"model": "mock", "input": ["network"]}).json()["data"][0]["embedding"]) == 8


def test_parameter_dataset_and_dynamic_protocols():
    assert client.post("/rest/parameter-options/scopes", json={}).json()["options"]
    assert client.post("/rest/dte/v1/onequery/uql/query", json={"query": "select * from network_health", "context": {}}).json()["data"]["results"]
    assert client.post("/rest/datasets/availability-trend", json={"parameters": {}, "context": {}}).json()["data"]["results"]
    assert client.post("/rest/dynamic-content/flow-section", json={}).json()["meta"]["dslType"] == "Section"


def test_guardrail_protocols_use_formal_naie_paths_only():
    assert client.post("/rest/naie/guardrail/v1/question/check", json={"question": "hello"}).json()["status"] is False
    assert client.post("/rest/naie/guardrail/v1/answer/check", json={"answer": "ok"}).json()["status"] is False
    assert client.post("/rest/naie/guardrail/v1/application-sec/check", json={"kind": "sql", "content": "select 1"}).json()["status"] is False


def test_policy_authentication_protocol():
    payload = {"userId": "user_001", "requests": [{"requestId": "req_1", "action": "dte.bi.chat.edit"}]}
    assert client.post("/rest/plat/priv/v1/policy/authentication", json=payload).json() == {"results": [{"result": True}]}
    denied = client.post("/rest/plat/priv/v1/policy/authentication", json=payload, headers={"X-Mock-Scenario": "deny"}).json()
    assert denied["results"][0]["result"] is False
    assert client.post("/rest/plat/priv/v1/policy/authentication", json=payload, headers={"X-Mock-Scenario": "error"}).status_code == 500
    assert client.post("/rest/plat/priv/v1/policy/authentication", json=payload, headers={"X-Mock-Scenario": "timeout"}).status_code == 504


def test_header_scenarios_are_request_scoped():
    assert client.post("/rest/datasets/availability-trend", headers={"X-Mock-Scenario": "empty"}, json={}).json()["data"]["results"] == []
    assert client.post("/rest/datasets/availability-trend", headers={"X-Mock-Scenario": "business-error"}, json={}).json() == {
        "retCode": 1001,
        "retInfo": "mock dataset business error",
    }
    assert client.post("/rest/datasets/availability-trend", headers={"X-Mock-Scenario": "error"}, json={}).status_code == 500
    assert client.post("/rest/datasets/availability-trend", headers={"X-Mock-Scenario": "timeout"}, json={}).status_code == 504
    assert client.post("/rest/datasets/availability-trend", json={}).json()["data"]["results"]


def test_onequery_exposes_known_string_business_errors():
    payload = {"query": "select * from network_health", "context": {}}

    assert client.post(
        "/rest/dte/v1/onequery/uql/query",
        headers={"X-Mock-Scenario": "unsupported-syntax"},
        json=payload,
    ).json() == {"retCode": "04003", "retInfo": "dblink does not support connect by"}
    assert client.post(
        "/rest/dte/v1/onequery/uql/query",
        headers={"X-Mock-Scenario": "field-not-found"},
        json=payload,
    ).json() == {"retCode": "04023", "retInfo": "query field does not exist"}


def test_datacatalog_list_returns_summaries_and_detail_returns_complete_logical_entity():
    summaries = client.post("/rest/odae/v3/datacatalog/model/logicalentities/list", json={}).json()["data"]["results"]
    detail = client.get(
        "/rest/odae/v3/datacatalog/model/logicalentity",
        params={"logicalEntityName": "network_health"},
    ).json()["data"]

    assert summaries[0]["name"] == "network_health"
    assert "schema" not in summaries[0]
    assert detail["schema"]["type"] == "record"
    assert {item["columnType"] for item in detail["schema"]["fields"]} == {"dimension", "measure", "timestamp"}
    assert any(item["type"]["type"] == "object" for item in detail["schema"]["fields"])


def test_agentcore_import_is_upsert():
    client.post("/__mock__/reset")
    conversation_id = client.post("/rest/naie/aiagentcore/v1/conversation", json={"title": "test"}).json()["conversationId"]
    chat_id = client.post("/rest/naie/aiagentcore/v1/chat/create", json={"conversationId": conversation_id, "question": "hello"}).json()["chatId"]
    first_piu = json.dumps(
        {
            "piuName": "ReportGenerationPIU",
            "answers": {
                "steps": [],
                "ask": {
                    "status": "pending",
                    "mode": "form",
                    "type": "confirm_params",
                    "title": "请确认报告诉求",
                    "text": "请确认报告诉求后开始生成。",
                },
                "delta": [],
                "answer": None,
                "errors": [],
            },
        },
        ensure_ascii=False,
    )
    payload = {
        "conversationId": conversation_id,
        "chatId": chat_id,
        "question": "hello",
        "askTime": 1780368000000,
        "answers": [
            {"type": "TEXT", "content": "已收到请求，正在分析报告诉求。", "answerTime": 1780368000100},
            {"type": "PIU", "content": first_piu, "answerTime": 1780368000300},
        ],
    }
    assert client.post("/rest/naie/aiagent/v1/chat/import", json=payload).status_code == 200
    updated_piu = json.dumps(
        {
            "piuName": "ReportGenerationPIU",
            "answers": {
                "steps": [],
                "ask": None,
                "delta": [],
                "answer": {"answerType": "REPORT", "answer": {"reportId": "rpt_001"}},
                "errors": [],
            },
        },
        ensure_ascii=False,
    )
    payload["answers"] = [{"type": "PIU", "content": updated_piu, "answerTime": 1780368000500}]
    assert client.post("/rest/naie/aiagent/v1/chat/import", json=payload).status_code == 200
    record = client.get(f"/rest/naie/aiagentcore/v1/chat/detail/{chat_id}").json()
    assert record["question"] == '{"content": "hello"}'
    assert record["askTime"] == 1780368000000
    assert record["answers"][0]["type"] == "PIU"
    assert json.loads(record["answers"][0]["content"])["answers"]["answer"]["answer"]["reportId"] == "rpt_001"


def test_agentcore_history_roundtrip_preserves_pending_ask_piu_content():
    client.post("/__mock__/reset")
    conversation_id = client.post("/rest/naie/aiagentcore/v1/conversation", json={"title": "test"}).json()["conversationId"]
    chat_id = client.post("/rest/naie/aiagentcore/v1/chat/create", json={"conversationId": conversation_id, "question": "hello"}).json()["chatId"]
    piu_content = json.dumps(
        {
            "piuName": "ReportGenerationPIU",
            "answers": {
                "steps": [{"stepId": "report.parameters.resolve", "title": "提取和确认生成条件", "status": "running"}],
                "ask": {
                    "status": "pending",
                    "mode": "form",
                    "type": "confirm_params",
                    "title": "请确认报告诉求",
                    "text": "请确认报告诉求后开始生成。",
                    "reportContext": {"templateInstance": {"id": "ti_001"}},
                },
                "delta": [],
                "answer": None,
                "errors": [],
            },
        },
        ensure_ascii=False,
    )
    assert (
        client.post(
            "/rest/naie/aiagent/v1/chat/import",
            json={
                "conversationId": conversation_id,
                "chatId": chat_id,
                "question": "hello",
                "askTime": 1780368000000,
                "answers": [{"type": "PIU", "content": piu_content, "answerTime": 1780368000300}],
            },
        ).status_code
        == 200
    )

    history = client.post("/rest/naie/aiagentcore/v2/chat/history", json={"conversationId": conversation_id}).json()
    record = history["records"][0]
    payload = json.loads(record["answers"][0]["content"])
    assert payload["piuName"] == "ReportGenerationPIU"
    assert payload["answers"]["ask"]["status"] == "pending"
    assert payload["answers"]["ask"]["type"] == "confirm_params"
