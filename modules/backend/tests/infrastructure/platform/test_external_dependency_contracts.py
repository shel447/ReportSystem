from __future__ import annotations

import json
from pathlib import Path
import re

import pytest
from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource


PROJECT_ROOT = Path(__file__).resolve().parents[5]
SCHEMA_ROOT = PROJECT_ROOT / "docs" / "implementation" / "contracts" / "schemas"
EXAMPLES = json.loads((SCHEMA_ROOT / "examples" / "external-dependencies.example.json").read_text(encoding="utf-8"))


def _schema(name: str) -> dict:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def _registry() -> Registry:
    registry = Registry()
    for path in SCHEMA_ROOT.glob("*.schema.json"):
        registry = registry.with_resource(path.as_uri(), Resource.from_contents(_schema(path.name)))
    return registry


REGISTRY = _registry()


def _validator(schema: dict) -> Draft202012Validator:
    return Draft202012Validator(schema, registry=REGISTRY)


def _validate(schema_name: str, definition: str, payload: dict) -> None:
    schema_uri = (SCHEMA_ROOT / schema_name).as_uri()
    _validator({"$ref": f"{schema_uri}#/$defs/{definition}"}).validate(payload)


@pytest.mark.parametrize(
    ("schema_name", "definition", "payload"),
    [
        ("openai-compatible.schema.json", "ChatCompletionRequest", EXAMPLES["openaiCompatible"]["chatCompletion"]["request"]),
        ("openai-compatible.schema.json", "ChatCompletionResponse", EXAMPLES["openaiCompatible"]["chatCompletion"]["response"]),
        ("openai-compatible.schema.json", "EmbeddingRequest", EXAMPLES["openaiCompatible"]["embedding"]["request"]),
        ("openai-compatible.schema.json", "EmbeddingResponse", EXAMPLES["openaiCompatible"]["embedding"]["response"]),
        ("agentcore.schema.json", "CreateConversationRequest", EXAMPLES["agentcore"]["createConversation"]["request"]),
        ("agentcore.schema.json", "CreateConversationResponse", EXAMPLES["agentcore"]["createConversation"]["response"]),
        ("agentcore.schema.json", "CreateChatRequest", EXAMPLES["agentcore"]["createChat"]["request"]),
        ("agentcore.schema.json", "CreateChatResponse", EXAMPLES["agentcore"]["createChat"]["response"]),
        ("agentcore.schema.json", "ImportChatRequest", EXAMPLES["agentcore"]["importChat"]["request"]),
        ("agentcore.schema.json", "ImportChatResponse", EXAMPLES["agentcore"]["importChat"]["response"]),
        ("agentcore.schema.json", "HistoryRequest", EXAMPLES["agentcore"]["history"]["request"]),
        ("agentcore.schema.json", "HistoryResponse", EXAMPLES["agentcore"]["history"]["response"]),
        ("agentcore.schema.json", "GetChatDetailRequest", EXAMPLES["agentcore"]["chatDetail"]["request"]),
        ("agentcore.schema.json", "ChatDetailResponse", EXAMPLES["agentcore"]["chatDetail"]["response"]),
        ("agentcore.schema.json", "ConversationListRequest", EXAMPLES["agentcore"]["conversations"]["request"]),
        ("agentcore.schema.json", "ConversationListResponse", EXAMPLES["agentcore"]["conversations"]["response"]),
        ("guardrail.schema.json", "QuestionCheckRequest", EXAMPLES["guardrail"]["questionCheck"]["request"]),
        ("guardrail.schema.json", "AnswerCheckRequest", EXAMPLES["guardrail"]["answerCheck"]["request"]),
        ("guardrail.schema.json", "LegalCheckResponse", EXAMPLES["guardrail"]["questionCheck"]["response"]),
        ("guardrail.schema.json", "ApplicationSecurityRequest", EXAMPLES["guardrail"]["applicationSecurity"]["request"]),
        ("guardrail.schema.json", "ApplicationSecurityResponse", EXAMPLES["guardrail"]["applicationSecurity"]["response"]),
        ("datacatalog.schema.json", "ListLogicalEntitiesRequest", EXAMPLES["datacatalog"]["listLogicalEntities"]["request"]),
        ("datacatalog.schema.json", "ListLogicalEntitiesResponse", EXAMPLES["datacatalog"]["listLogicalEntities"]["response"]),
        ("datacatalog.schema.json", "GetLogicalEntityRequest", EXAMPLES["datacatalog"]["logicalEntity"]["request"]),
        ("datacatalog.schema.json", "GetLogicalEntityResponse", EXAMPLES["datacatalog"]["logicalEntity"]["response"]),
        ("datacatalog.schema.json", "GetDatasetRequest", EXAMPLES["datacatalog"]["dataset"]["request"]),
        ("datacatalog.schema.json", "GetDatasetResponse", EXAMPLES["datacatalog"]["dataset"]["response"]),
        ("datacatalog.schema.json", "ListLogicalRelationsRequest", EXAMPLES["datacatalog"]["listLogicalRelations"]["request"]),
        ("datacatalog.schema.json", "ListLogicalRelationsResponse", EXAMPLES["datacatalog"]["listLogicalRelations"]["response"]),
        ("datacatalog.schema.json", "GetLogicalRelationRequest", EXAMPLES["datacatalog"]["logicalRelation"]["request"]),
        ("datacatalog.schema.json", "GetLogicalRelationResponse", EXAMPLES["datacatalog"]["logicalRelation"]["response"]),
        ("knowledge-rag.schema.json", "QueryKnowledgeRequest", EXAMPLES["knowledgeRag"]["knowledge"]["request"]),
        ("knowledge-rag.schema.json", "QueryKnowledgeResponse", EXAMPLES["knowledgeRag"]["knowledge"]["response"]),
        ("knowledge-rag.schema.json", "RetrieveKnowledgeRequest", EXAMPLES["knowledgeRag"]["retrieveKnowledge"]["request"]),
        ("knowledge-rag.schema.json", "RetrieveKnowledgeResponse", EXAMPLES["knowledgeRag"]["retrieveKnowledge"]["response"]),
        ("knowledge-rag.schema.json", "RetrieveMultiIndexRequest", EXAMPLES["knowledgeRag"]["retrieveMultiIndex"]["request"]),
        ("knowledge-rag.schema.json", "RetrieveMultiIndexResponse", EXAMPLES["knowledgeRag"]["retrieveMultiIndex"]["response"]),
        ("nodeagent.schema.json", "AppConfigRequest", EXAMPLES["nodeAgent"]["appConfig"]["request"]),
        ("nodeagent.schema.json", "AppConfigResponse", EXAMPLES["nodeAgent"]["appConfig"]["response"]),
        ("metadata-sync.schema.json", "PackageRegisterProcessRequest", EXAMPLES["metadataSync"]["packageRegisterProcess"]["request"]),
        ("metadata-sync.schema.json", "PackageRegisterProcessResponse", EXAMPLES["metadataSync"]["packageRegisterProcess"]["response"]),
        ("audit.schema.json", "AuditEventRequest", EXAMPLES["audit"]["operation"]["request"]),
        ("audit.schema.json", "AuditResponse", EXAMPLES["audit"]["operation"]["response"]),
        ("onequery.schema.json", "OneQueryRequest", EXAMPLES["dataQuery"]["oneQuery"]["request"]),
        ("onequery.schema.json", "OneQueryResponse", EXAMPLES["dataQuery"]["response"]),
        ("api-dataset.schema.json", "ApiDatasetRequest", EXAMPLES["dataQuery"]["apiDataset"]["request"]),
        ("api-dataset.schema.json", "ApiDatasetResponse", EXAMPLES["dataQuery"]["response"]),
    ],
)
def test_external_dependency_examples_match_consumer_contracts(schema_name, definition, payload):
    _validate(schema_name, definition, payload)


def test_agentcore_import_contract_is_an_upsert_payload():
    payload = EXAMPLES["agentcore"]["importChat"]["request"]

    assert payload["conversationId"] == "conv_001"
    assert payload["chatId"] == "chat_001"
    assert payload["question"] == "生成总部网络运行日报"
    assert isinstance(payload["answers"], list)
    assert "content" not in payload
    piu_payloads = [json.loads(item["content"]) for item in payload["answers"] if item["type"] == "PIU"]
    assert piu_payloads[0]["piuName"] == "ReportGenerationPIU"
    assert piu_payloads[0]["answers"]["steps"][0]["stepId"] == "step_root"
    assert piu_payloads[-1]["answers"]["answer"]["answerType"] == "REPORT"
    _validate("agentcore.schema.json", "ImportChatRequest", payload)


def test_platform_response_contracts_allow_additional_fields():
    payload = {**EXAMPLES["agentcore"]["createConversation"]["response"], "platformExtension": {"traceId": "trace_001"}}

    _validate("agentcore.schema.json", "CreateConversationResponse", payload)


def test_platform_response_contracts_reject_missing_consumed_fields():
    with pytest.raises(ValidationError):
        _validate("agentcore.schema.json", "CreateConversationResponse", {"platformExtension": True})


@pytest.mark.parametrize(
    "payload",
    [
        EXAMPLES["dataQuery"]["response"],
        {"retCode": 1001, "retInfo": "query failed"},
    ],
)
def test_onequery_and_api_dataset_responses_accept_the_same_envelopes(payload):
    _validate("onequery.schema.json", "OneQueryResponse", payload)
    _validate("api-dataset.schema.json", "ApiDatasetResponse", payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"retInfo": ""},
        {"retCode": 0, "retInfo": ""},
    ],
)
def test_onequery_and_api_dataset_responses_reject_the_same_invalid_envelopes(payload):
    with pytest.raises(ValidationError):
        _validate("onequery.schema.json", "OneQueryResponse", payload)
    with pytest.raises(ValidationError):
        _validate("api-dataset.schema.json", "ApiDatasetResponse", payload)


def test_schema_readme_indexes_every_top_level_schema_and_drops_retired_names():
    readme = (SCHEMA_ROOT / "README.md").read_text(encoding="utf-8")
    schema_names = {path.name for path in SCHEMA_ROOT.glob("*.schema.json")}

    assert schema_names <= set(re.findall(r"([a-z0-9-]+\.schema\.json)", readme))
    for retired in (
        "onequery-request.schema.json",
        "api-dataset-request.schema.json",
        "dataset-source-response.schema.json",
        "platform-runtime.schema.json",
    ):
        assert retired not in readme


def test_schema_readme_fragment_links_resolve():
    readme = (SCHEMA_ROOT / "README.md").read_text(encoding="utf-8")

    for schema_name, definition in re.findall(r"\(([-a-z0-9]+\.schema\.json)#/\$defs/([A-Za-z0-9]+)\)", readme):
        assert definition in _schema(schema_name)["$defs"], f"{schema_name}#/$defs/{definition}"
