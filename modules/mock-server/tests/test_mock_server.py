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


def test_header_scenarios_are_request_scoped():
    assert client.post("/rest/datasets/availability-trend", headers={"X-Mock-Scenario": "empty"}, json={}).json()["data"]["results"] == []
    assert client.post("/rest/datasets/availability-trend", headers={"X-Mock-Scenario": "business-error"}, json={}).json() == {
        "retCode": 1001,
        "retInfo": "mock dataset business error",
    }
    assert client.post("/rest/datasets/availability-trend", headers={"X-Mock-Scenario": "error"}, json={}).status_code == 500
    assert client.post("/rest/datasets/availability-trend", headers={"X-Mock-Scenario": "timeout"}, json={}).status_code == 504
    assert client.post("/rest/datasets/availability-trend", json={}).json()["data"]["results"]


def test_agentcore_import_is_upsert():
    client.post("/__mock__/reset")
    conversation_id = client.post("/rest/naie/aiagentcore/v1/conversation", json={"title": "test"}).json()["conversationId"]
    chat_id = client.post("/rest/naie/aiagentcore/v1/chat/create", json={"conversationId": conversation_id, "question": "hello"}).json()["chatId"]
    payload = {"conversationId": conversation_id, "chatId": chat_id, "type": "PIU", "content": {"answers": {"response": {"status": "first"}}}}
    assert client.post("/rest/naie/aiagent/v1/chat/import", json=payload).status_code == 200
    payload["content"]["answers"]["response"]["status"] = "updated"
    assert client.post("/rest/naie/aiagent/v1/chat/import", json=payload).status_code == 200
    record = client.get(f"/rest/naie/aiagentcore/v1/chat/detail/{chat_id}").json()
    assert record["answers"][0]["content"]["response"]["status"] == "updated"
