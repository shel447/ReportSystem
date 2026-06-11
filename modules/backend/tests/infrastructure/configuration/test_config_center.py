from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.shared.configuration import (
    AIConfiguration,
    ConfigCenter,
    ConfigKey,
    DataAnalysisConfiguration,
    KnowledgeConfiguration,
    LLMConfiguration,
)
from src.infrastructure.configuration.sources import (
    EnvironmentConfigSource,
    NodeAgentAppConfigSource,
    RuntimeIniConfigSource,
)
from src.infrastructure.configuration import providers


@dataclass
class Source:
    name: str
    payload: dict

    def load(self):
        return self.payload


def _center() -> tuple[ConfigCenter, ConfigKey, ConfigKey, ConfigKey, ConfigKey]:
    ai = ConfigKey("ai", AIConfiguration.from_mapping, required=True)
    llm = ConfigKey("llm", LLMConfiguration.from_mapping, required=True)
    knowledge = ConfigKey("knowledge", KnowledgeConfiguration.from_mapping)
    analysis = ConfigKey("dataAnalysis", DataAnalysisConfiguration.from_mapping)
    return ConfigCenter(keys=(ai, llm, knowledge, analysis)), ai, llm, knowledge, analysis


def test_config_center_merges_partial_sources_in_registration_order():
    center, ai_key, llm_key, knowledge_key, analysis_key = _center()

    snapshot = center.initialize(
        (
            Source(
                "runtime.ini",
                {
                    "ai": {
                        "embedding": {
                            "baseUrl": "https://embedding.example/v1",
                            "model": "embedding-model",
                            "apiKey": "embedding-secret",
                        },
                    },
                    "llm": {
                        "defaultLlm": "qwen3_32b",
                        "inferParams": {"stream": True, "temperature": 0.2},
                        "candidateLlms": {
                            "qwen3_32b": {
                                "baseUrl": "https://model.example/v1",
                                "modelName": "qwen3-32b",
                            }
                        },
                    },
                    "knowledge": {
                        "nl2sql": {"indexName": "ini-index"},
                        "index": {"chatbi_sql_few_shot": "few-shot-v1"},
                    },
                },
            ),
            Source(
                "database",
                {
                    "llm": {
                        "candidateLlms": {
                            "qwen3_32b": {
                                "inferParams": {"temperature": 0.4},
                            }
                        }
                    }
                },
            ),
            Source(
                "environment",
                {
                    "knowledge": {"nl2sql": {"indexName": "env-index"}},
                    "dataAnalysis": {"queryStrategy": "ibis_planner"},
                },
            ),
        )
    )

    assert center.get(ai_key).embedding.api_key == "embedding-secret"
    candidate = center.get(llm_key).resolve()
    assert candidate.model_name == "qwen3-32b"
    assert candidate.infer_params == {"stream": True, "temperature": 0.4}
    assert center.get(knowledge_key).nl2sql_index_name == "env-index"
    assert center.get(knowledge_key).index.chatbi_sql_few_shot == "few-shot-v1"
    assert center.get(analysis_key).query_strategy == "ibis_planner"
    assert snapshot.sources["knowledge"]["nl2sql.indexName"] == "environment"


def test_config_center_snapshot_is_read_only_and_secret_repr_is_masked():
    center, ai_key, llm_key, _knowledge, _analysis = _center()
    snapshot = center.initialize(
        (
            Source(
                "database",
                {
                    "ai": {
                        "embedding": {
                            "baseUrl": "https://embedding.example/v1",
                            "model": "embedding-model",
                            "apiKey": "top-secret",
                        },
                    },
                    "llm": {
                        "defaultLlm": "qwen3_32b",
                        "candidateLlms": {
                            "qwen3_32b": {
                                "baseUrl": "",
                                "modelName": "",
                            }
                        },
                    },
                },
            ),
        )
    )

    assert "top-secret" not in repr(center.get(ai_key))
    with pytest.raises(ValueError, match="LLM candidate configuration is incomplete"):
        center.get(llm_key).resolve()
    with pytest.raises(TypeError):
        snapshot.values["ai"] = object()


def test_config_center_rejects_missing_required_ai_configuration():
    center, _ai, _llm, _knowledge, _analysis = _center()

    with pytest.raises(ValueError, match="AI embedding configuration is incomplete"):
        center.initialize(())


def test_llm_configuration_rejects_missing_default_candidate():
    with pytest.raises(ValueError, match="does not exist"):
        LLMConfiguration.from_mapping(
            {
                "defaultLlm": "missing",
                "candidateLlms": {
                    "qwen3_32b": {
                        "modelName": "qwen3-32b",
                        "baseUrl": "https://model.example/v1",
                    }
                },
            }
        )


def test_llm_explicit_infer_params_override_candidate_and_global_defaults():
    configuration = LLMConfiguration.from_mapping(
        {
            "defaultLlm": "qwen3_32b",
            "inferParams": {"stream": True, "temperature": 0.2},
            "candidateLlms": {
                "qwen3_32b": {
                    "modelName": "qwen3-32b",
                    "baseUrl": "https://model.example/v1",
                    "inferParams": {"temperature": 0.4},
                }
            },
        }
    )

    candidate = configuration.resolve(infer_params={"temperature": 0.7, "max_tokens": 512})

    assert candidate.infer_params == {
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 512,
    }


def test_runtime_ini_source_maps_business_sections():
    class FakeIni:
        values = {
            "chatbi.ai.completion": [
                ("base_url", "https://model.example/v1"),
                ("model", "legacy-model"),
                ("temperature", "0.4"),
            ],
            "chatbi.ai.embedding": [
                ("model", "embedding-model"),
                ("use_completion_auth", "true"),
            ],
            "chatbi.llm": [("default_llm", "qwen3_32b")],
            "chatbi.llm.infer_params": [("stream", "true")],
            "chatbi.llm.candidate_llms.qwen3_32b": [
                ("model_name", "qwen3-32b"),
                ("base_url", "https://qwen.example/v1"),
            ],
            "chatbi.knowledge.index": [
                ("chatbi_sql_few_shot", "chatbi-sql-few-shot"),
            ],
            "chatbi.knowledge.nl2sql": [("index_name", "network-index")],
            "chatbi.data_analysis": [("query_strategy", "ibis_planner")],
        }

        def items(self, section):
            return self.values.get(section, ())

        def sections(self):
            return list(self.values)

    payload = RuntimeIniConfigSource(ini=FakeIni()).load()

    assert payload["ai"]["embedding"]["baseUrl"] == "https://model.example/v1"
    assert payload["llm"]["defaultLlm"] == "qwen3_32b"
    assert payload["llm"]["inferParams"]["stream"] is True
    assert payload["llm"]["candidateLlms"]["qwen3_32b"]["modelName"] == "qwen3-32b"
    assert payload["knowledge"]["index"]["chatbiSqlFewShot"] == "chatbi-sql-few-shot"
    assert payload["knowledge"]["nl2sql"]["indexName"] == "network-index"
    assert payload["dataAnalysis"]["queryStrategy"] == "ibis_planner"


def test_nodeagent_source_ignores_platform_external_services():
    class Client:
        def get_json(self, **_kwargs):
            return {
                "externalServices": {"onequery": {"baseUrl": "https://ignored"}},
                "chatbi": {
                    "llm": {
                        "default_llm": "qwen3_32b",
                        "candidate_llms": {"qwen3_32b": {}},
                    },
                    "knowledge": {
                        "index": {"chatbi_sql_few_shot": "few-shot"},
                        "nl2sql": {"indexName": "network-index"},
                    }
                },
            }

    payload = NodeAgentAppConfigSource(client=Client()).load()

    assert payload == {
        "llm": {
            "default_llm": "qwen3_32b",
            "candidate_llms": {"qwen3_32b": {}},
        },
        "knowledge": {
            "index": {"chatbi_sql_few_shot": "few-shot"},
            "nl2sql": {"indexName": "network-index"},
        }
    }
    assert "externalServices" not in payload


def test_environment_source_only_exposes_chatbi_business_compatibility(monkeypatch):
    monkeypatch.setenv("REPORT_QUERY_STRATEGY", "ibis_planner")
    monkeypatch.setenv("CHATBI_COMPLETION_MODEL", "chat-model")

    payload = EnvironmentConfigSource().load()

    assert payload["dataAnalysis"]["queryStrategy"] == "ibis_planner"
    assert payload["llm"]["defaultLlm"] == "environment_completion"
    assert (
        payload["llm"]["candidateLlms"]["environment_completion"]["modelName"]
        == "chat-model"
    )


def test_environment_source_maps_new_llm_and_knowledge_index_variables(monkeypatch):
    monkeypatch.setenv("CHATBI_LLM_DEFAULT_LLM", "qwen3_32b")
    monkeypatch.setenv("CHATBI_LLM_MODEL_NAME", "qwen3-32b")
    monkeypatch.setenv("CHATBI_LLM_BASE_URL", "/v1")
    monkeypatch.setenv("CHATBI_LLM_STREAM", "true")
    monkeypatch.setenv("CHATBI_SQL_FEW_SHOT", "sql-few-shot-v2")

    payload = EnvironmentConfigSource().load()

    assert payload["llm"] == {
        "defaultLlm": "qwen3_32b",
        "inferParams": {"stream": True},
        "candidateLlms": {
            "qwen3_32b": {
                "modelName": "qwen3-32b",
                "baseUrl": "/v1",
            }
        },
    }
    assert payload["knowledge"]["index"]["chatbi_sql_few_shot"] == "sql-few-shot-v2"


def test_completion_provider_uses_llm_candidate_instead_of_ai_completion(monkeypatch):
    configuration = LLMConfiguration.from_mapping(
        {
            "defaultLlm": "qwen3_32b",
            "inferParams": {"stream": True, "temperature": 0.3},
            "candidateLlms": {
                "qwen3_32b": {
                    "modelName": "qwen3-32b",
                    "baseUrl": "/v1",
                    "inferParams": {"timeoutSeconds": 45},
                }
            },
        }
    )
    monkeypatch.setattr(providers, "get_llm_configuration", lambda: configuration)

    provider = providers.build_completion_provider_config()

    assert provider.base_url == "/v1"
    assert provider.model == "qwen3-32b"
    assert provider.api_key == ""
    assert provider.timeout_sec == 45
    assert provider.infer_params == {"stream": True, "temperature": 0.3}
