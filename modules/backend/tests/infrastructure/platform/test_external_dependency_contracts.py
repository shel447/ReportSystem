from __future__ import annotations

import json
from pathlib import Path

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
        ("agentcore.schema.json", "ChatDetailResponse", EXAMPLES["agentcore"]["chatDetail"]["response"]),
        ("agentcore.schema.json", "ConversationListResponse", EXAMPLES["agentcore"]["conversations"]["response"]),
        ("guardrail.schema.json", "QuestionCheckRequest", EXAMPLES["guardrail"]["questionCheck"]["request"]),
        ("guardrail.schema.json", "AnswerCheckRequest", EXAMPLES["guardrail"]["answerCheck"]["request"]),
        ("guardrail.schema.json", "LegalCheckResponse", EXAMPLES["guardrail"]["questionCheck"]["response"]),
        ("guardrail.schema.json", "ApplicationSecurityRequest", EXAMPLES["guardrail"]["applicationSecurity"]["request"]),
        ("guardrail.schema.json", "ApplicationSecurityResponse", EXAMPLES["guardrail"]["applicationSecurity"]["response"]),
        ("datacatalog.schema.json", "PagedFilterRequest", EXAMPLES["datacatalog"]["listLogicalEntities"]["request"]),
        ("datacatalog.schema.json", "SuccessListResponse", EXAMPLES["datacatalog"]["listLogicalEntities"]["response"]),
        ("datacatalog.schema.json", "OpenDataResponse", EXAMPLES["datacatalog"]["logicalEntity"]["response"]),
        ("datacatalog.schema.json", "SuccessDataResponse", EXAMPLES["datacatalog"]["logicalRelation"]["response"]),
        ("knowledge-rag.schema.json", "KnowledgeQueryResponse", EXAMPLES["knowledgeRag"]["knowledge"]["response"]),
        ("knowledge-rag.schema.json", "RetrieveKnowledgeRequest", EXAMPLES["knowledgeRag"]["retrieveKnowledge"]["request"]),
        ("knowledge-rag.schema.json", "RetrieveResponse", EXAMPLES["knowledgeRag"]["retrieveKnowledge"]["response"]),
        ("knowledge-rag.schema.json", "RetrieveMultiIndexRequest", EXAMPLES["knowledgeRag"]["retrieveMultiIndex"]["request"]),
        ("platform-runtime.schema.json", "NodeAgentAppConfigResponse", EXAMPLES["platformRuntime"]["nodeAgent"]["response"]),
        ("platform-runtime.schema.json", "MetadataSyncResponse", EXAMPLES["platformRuntime"]["metadataSync"]["response"]),
        ("audit.schema.json", "AuditEventRequest", EXAMPLES["audit"]["operation"]["request"]),
        ("audit.schema.json", "AuditResponse", EXAMPLES["audit"]["operation"]["response"]),
        ("onequery-request.schema.json", None, EXAMPLES["dataQuery"]["oneQuery"]["request"]),
        ("api-dataset-request.schema.json", None, EXAMPLES["dataQuery"]["apiDataset"]["request"]),
        ("dataset-source-response.schema.json", None, EXAMPLES["dataQuery"]["response"]),
    ],
)
def test_external_dependency_examples_match_consumer_contracts(schema_name, definition, payload):
    if definition is None:
        _validator({"$ref": (SCHEMA_ROOT / schema_name).as_uri()}).validate(payload)
    else:
        _validate(schema_name, definition, payload)


def test_agentcore_import_contract_is_an_upsert_payload():
    payload = EXAMPLES["agentcore"]["importChat"]["request"]

    assert payload["conversationId"] == "conv_001"
    assert payload["chatId"] == "chat_001"
    assert payload["content"]["answers"]["response"]["status"] == "available"
    _validate("agentcore.schema.json", "ImportChatRequest", payload)


def test_platform_response_contracts_allow_additional_fields():
    payload = {**EXAMPLES["agentcore"]["createConversation"]["response"], "platformExtension": {"traceId": "trace_001"}}

    _validate("agentcore.schema.json", "CreateConversationResponse", payload)


def test_platform_response_contracts_reject_missing_consumed_fields():
    with pytest.raises(ValidationError):
        _validate("agentcore.schema.json", "CreateConversationResponse", {"platformExtension": True})
