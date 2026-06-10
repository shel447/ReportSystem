"""可插拔开发态外部业务服务替身。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from threading import RLock
import time
from typing import Any
import uuid

from fastapi import FastAPI, Header, HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_PATH = PROJECT_ROOT / "testdata" / "mock-server" / "responses.json"


def _load_fixtures() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _apply_scenario(scenario: str | None, *, empty: Any) -> Any | None:
    if scenario == "timeout":
        raise HTTPException(status_code=504, detail="mock timeout")
    if scenario == "error":
        raise HTTPException(status_code=500, detail="mock error")
    return empty if scenario == "empty" else None


def _dataset_response(dataset: dict[str, Any]) -> dict[str, Any]:
    return {"retCode": 0, "retInfo": "", "data": dataset}


def _dataset_business_error() -> dict[str, Any]:
    return {"retCode": 1001, "retInfo": "mock dataset business error"}


def _normalize_import_answers(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_answers = payload.get("answers")
    if isinstance(raw_answers, list):
        answers: list[dict[str, Any]] = []
        for item in raw_answers:
            if not isinstance(item, dict):
                continue
            answer = {
                "type": str(item.get("type") or ""),
                "content": item.get("content"),
                "answerTime": item.get("answerTime"),
            }
            if isinstance(answer["content"], dict):
                answer["content"] = json.dumps(answer["content"], ensure_ascii=False)
            answers.append(answer)
        return answers

    # Historical mock payload shape used before AgentCore records were aligned.
    legacy_answers = payload.get("content", {}).get("answers") if isinstance(payload.get("content"), dict) else None
    if isinstance(legacy_answers, dict):
        return [
            {
                "type": "PIU",
                "content": json.dumps({"piuName": "ReportGenerationPIU", "answers": legacy_answers}, ensure_ascii=False),
                "answerTime": payload.get("answerTime"),
            }
        ]
    return []


def _last_message_preview(answers: list[dict[str, Any]]) -> str:
    for answer in reversed(answers):
        if answer.get("type") == "TEXT":
            return str(answer.get("content") or "")[:120]
        if answer.get("type") != "PIU":
            continue
        content = answer.get("content")
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except ValueError:
                continue
        if not isinstance(content, dict):
            continue
        piu_answers = content.get("answers")
        if not isinstance(piu_answers, dict):
            continue
        if piu_answers.get("answer") is not None:
            return "finished"
        ask = piu_answers.get("ask")
        if isinstance(ask, dict):
            return str(ask.get("type") or "waiting_user")
        errors = piu_answers.get("errors") or []
        if errors:
            return "failed"
    return ""


def create_app() -> FastAPI:
    app = FastAPI(title="ReportSystem Mock External Service")
    conversations: dict[str, dict[str, Any]] = {}
    chats: dict[str, dict[str, Any]] = {}
    lock = RLock()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/rest/plat/priv/v1/policy/authentication")
    def policy_authentication(payload: dict[str, Any], x_mock_scenario: str | None = Header(default=None)):
        if x_mock_scenario == "timeout":
            raise HTTPException(status_code=504, detail="mock timeout")
        if x_mock_scenario == "error":
            raise HTTPException(status_code=500, detail="mock error")
        allowed = x_mock_scenario not in {"deny", "denied", "unauthorized"}
        return {"results": [{"result": allowed} for _ in list(payload.get("requests") or [])]}

    @app.post("/v1/chat/completions")
    def chat_completions(payload: dict[str, Any], x_mock_scenario: str | None = Header(default=None)):
        empty = _apply_scenario(x_mock_scenario, empty="")
        messages = list(payload.get("messages") or [])
        system = str((messages[0] if messages else {}).get("content") or "")
        if empty is not None:
            content = empty
        elif "intent_function" in system:
            content = json.dumps(
                {
                    "sql": "select * from network_health",
                    "intent_function": "def resolve_intent(question):\n    return {'topic': 'network_health', 'question': question}",
                },
                ensure_ascii=False,
            )
        elif "简洁中文结论" in system:
            content = "查询结果显示网络设备健康状态整体稳定，建议优先关注评分较低的设备。"
        else:
            content = "completion test ok"
        return {"model": payload.get("model") or "mock-chat", "choices": [{"message": {"content": content}}]}

    @app.post("/v1/embeddings")
    def embeddings(payload: dict[str, Any], x_mock_scenario: str | None = Header(default=None)):
        empty = _apply_scenario(x_mock_scenario, empty=[])
        inputs = list(payload.get("input") or [])
        vectors = empty if empty is not None else [_embedding(str(item)) for item in inputs]
        return {"model": payload.get("model") or "mock-embedding", "data": [{"embedding": item} for item in vectors]}

    @app.post("/rest/parameter-options/{name}")
    def parameter_options(name: str, _: dict[str, Any], x_mock_scenario: str | None = Header(default=None)):
        empty = _apply_scenario(x_mock_scenario, empty={"options": [], "defaultValue": []})
        if empty is not None:
            return empty
        values = _load_fixtures()["parameterOptions"].get(name)
        if values is None:
            raise HTTPException(status_code=404, detail=f"unknown parameter options: {name}")
        return values

    @app.post("/rest/dte/v1/onequery/uql/query")
    def onequery(payload: dict[str, Any], x_mock_scenario: str | None = Header(default=None)):
        if x_mock_scenario == "business-error":
            return _dataset_business_error()
        if x_mock_scenario == "unsupported-syntax":
            return {"retCode": "04003", "retInfo": "dblink does not support connect by"}
        if x_mock_scenario == "field-not-found":
            return {"retCode": "04023", "retInfo": "query field does not exist"}
        empty = _apply_scenario(x_mock_scenario, empty=_dataset_response({"columns": {}, "results": []}))
        if empty is not None:
            return empty
        query = str(payload.get("query") or "").lower()
        key = next((item for item in _load_fixtures()["queryMatches"] if item in query), "default")
        return _dataset_response(_load_fixtures()["datasets"][key])

    @app.post("/rest/naie/guardrail/v1/question/check")
    def question_guardrail(payload: dict[str, Any], x_mock_scenario: str | None = Header(default=None)):
        _apply_scenario(x_mock_scenario, empty=None)
        blocked = x_mock_scenario == "blocked" or any("危险" in str(item) for item in list(payload.get("questions") or []))
        return {
            "status": blocked,
            "error_msg": "请求未通过安全检查" if blocked else None,
            "checkResults": [{"isLegal": not blocked, "response": "请求未通过安全检查" if blocked else ""}],
        }

    @app.post("/rest/naie/guardrail/v1/answer/check")
    def answer_guardrail(payload: dict[str, Any], x_mock_scenario: str | None = Header(default=None)):
        _apply_scenario(x_mock_scenario, empty=None)
        blocked = x_mock_scenario == "blocked"
        return {
            "status": blocked,
            "error_msg": "回答未通过安全检查" if blocked else None,
            "checkResults": [{"isLegal": not blocked, "response": "回答未通过安全检查" if blocked else ""}],
        }

    @app.post("/rest/naie/guardrail/v1/application-sec/check")
    def application_guardrail(payload: dict[str, Any], x_mock_scenario: str | None = Header(default=None)):
        _apply_scenario(x_mock_scenario, empty=None)
        blocked = x_mock_scenario == "blocked" or "drop table" in str(payload.get("content") or "").lower()
        return {
            "status": blocked,
            "error_msg": "生成内容存在风险" if blocked else None,
            "results": [{"isLegal": not blocked, "response": "生成内容存在风险" if blocked else ""}],
        }

    @app.post("/rest/naie/aiagentcore/v1/conversation")
    def create_conversation(payload: dict[str, Any]):
        conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
        with lock:
            conversations[conversation_id] = {
                "conversationId": conversation_id,
                "title": str(payload.get("title") or "新会话"),
                "status": "active",
                "updatedAt": int(time.time() * 1000),
            }
        return {"conversationId": conversation_id}

    @app.post("/rest/naie/aiagentcore/v1/chat/create")
    def create_chat(payload: dict[str, Any]):
        chat_id = f"chat_{uuid.uuid4().hex[:12]}"
        conversation_id = str(payload.get("conversationId") or "")
        with lock:
            if conversation_id not in conversations:
                raise HTTPException(status_code=404, detail="conversation not found")
            chats[chat_id] = {
                "id": chat_id,
                "chatId": chat_id,
                "conversationId": conversation_id,
                "question": json.dumps({"content": str(payload.get("question") or "")}, ensure_ascii=False),
                "answers": [],
                "askTime": int(time.time() * 1000),
            }
        return {"chatId": chat_id}

    @app.post("/rest/naie/aiagent/v1/chat/import")
    def import_chat(payload: dict[str, Any]):
        chat_id = str(payload.get("chatId") or "")
        conversation_id = str(payload.get("conversationId") or "")
        answers = _normalize_import_answers(payload)
        with lock:
            row = dict(chats.get(chat_id) or {"id": chat_id, "chatId": chat_id, "conversationId": conversation_id, "question": ""})
            if "question" in payload:
                row["question"] = json.dumps({"content": str(payload.get("question") or "")}, ensure_ascii=False)
            if payload.get("askTime") is not None:
                row["askTime"] = payload.get("askTime")
            row["answers"] = answers
            chats[chat_id] = row
            if conversation_id in conversations:
                conversations[conversation_id]["updatedAt"] = int(time.time() * 1000)
                conversations[conversation_id]["lastMessagePreview"] = _last_message_preview(answers)
        return {"status": "ok"}

    @app.post("/rest/naie/aiagentcore/v2/chat/history")
    def chat_history(payload: dict[str, Any]):
        conversation_id = str(payload.get("conversationId") or "")
        with lock:
            records = [dict(item) for item in chats.values() if item.get("conversationId") == conversation_id]
        records.sort(key=lambda item: int(item.get("askTime") or 0))
        return {"records": records, "total": len(records), "pageNum": int(payload.get("pageNum") or 1), "pageSize": int(payload.get("pageSize") or 10)}

    @app.get("/rest/naie/aiagentcore/v1/chat/detail/{chat_id}")
    def chat_detail(chat_id: str):
        with lock:
            row = chats.get(chat_id)
            if row is None:
                raise HTTPException(status_code=404, detail="chat not found")
            return dict(row)

    @app.get("/rest/naie/aiagentcore/v1/conversations")
    def list_conversations():
        with lock:
            return {"records": [dict(item) for item in conversations.values()]}

    @app.post("/rest/odae/v3/datacatalog/model/logicalentities/list")
    def logical_entities(_: dict[str, Any]):
        return {
            "retCode": 0,
            "retInfo": "",
            "data": {
                "results": [
                    {"name": "network_health", "description": "网络设备健康数据", "columns": ["device_name", "health_score", "status"]},
                    {"name": "network_alarm", "description": "网络告警数据", "columns": ["level", "count"]},
                ],
                "totalCount": 2,
            },
        }

    @app.get("/rest/odae/v3/datacatalog/model/logicalentity")
    def logical_entity(logicalEntityName: str):
        return {"data": {"name": logicalEntityName}}

    @app.get("/rest/odae/v3/datacatalog/model/datasets/{name}")
    def dataset_metadata(name: str):
        return {"data": {"name": name}}

    @app.post("/rest/dte/v2/datacatalog/product/model/logicalrelations/query")
    def logical_relations(_: dict[str, Any]):
        return {"retCode": 0, "retInfo": "", "data": {"results": [], "totalCount": 0}}

    @app.get("/rest/dte/v2/datacatalog/product/model/logicalrelation")
    def logical_relation(name: str):
        return {"retCode": 0, "retInfo": "", "data": {"name": name}}

    @app.get("/rest/naie/knwl/v1/knowledge")
    def knowledge():
        return {"total": 0, "ragIndex": "mock", "knowledgeList": []}

    @app.post("/rest/naie/rag/v1/retriever-klg")
    def retrieve_knowledge(_: dict[str, Any]):
        return {"query": "", "recommends": []}

    @app.post("/rest/naie/rag/v1/retriever")
    def retrieve_multi(_: dict[str, Any]):
        return {"query": "", "recommends": [{"id": "nl2sql_1", "description": "网络健康查询样例", "rerankScore": 0.9}]}

    @app.get("/rest/nodeagent/v2/csi/appconf")
    def app_config(watch: str = "false"):
        return {"externalServices": {"mock": True}, "watch": watch}

    @app.post("/rest/plat/audit/v1/logs")
    def operation_audit(_: dict[str, Any]):
        return {"status": "ok"}

    @app.post("/rest/plat/audit/v1/seculogs")
    def security_audit(_: dict[str, Any]):
        return {"status": "ok"}

    @app.get("/rest/entassistantservice/v1/chatbi/package/register/process")
    def metadata_sync():
        return {"status": "complete", "version": "mock-v1"}

    @app.post("/__mock__/reset")
    def reset():
        with lock:
            conversations.clear()
            chats.clear()
        return {"status": "ok"}

    @app.post("/rest/datasets/{name}")
    def api_dataset(name: str, _: dict[str, Any], x_mock_scenario: str | None = Header(default=None)):
        if x_mock_scenario == "business-error":
            return _dataset_business_error()
        empty = _apply_scenario(x_mock_scenario, empty=_dataset_response({"columns": {}, "results": []}))
        if empty is not None:
            return empty
        dataset = _load_fixtures()["datasets"].get(name)
        if dataset is None:
            raise HTTPException(status_code=404, detail=f"unknown dataset: {name}")
        return _dataset_response(dataset)

    @app.post("/rest/dynamic-content/{name}")
    def dynamic_content(name: str, _: dict[str, Any], x_mock_scenario: str | None = Header(default=None)):
        empty = _apply_scenario(x_mock_scenario, empty={"status": "success", "dsl": [], "meta": {"dslType": "Components"}})
        if empty is not None:
            return empty
        payload = _load_fixtures()["dynamicContent"].get(name)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"unknown dynamic content: {name}")
        return payload

    return app


def _embedding(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [round((value - 127.5) / 127.5, 6) for value in digest[:8]]


app = create_app()
