from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.shared.configuration import (
    AIConfiguration,
    ConfigCenter,
    ConfigKey,
    DataAnalysisConfiguration,
    KnowledgeConfiguration,
)
from src.infrastructure.configuration.sources import (
    EnvironmentConfigSource,
    NodeAgentAppConfigSource,
    RuntimeIniConfigSource,
)


@dataclass
class Source:
    name: str
    payload: dict

    def load(self):
        return self.payload


def _center() -> tuple[ConfigCenter, ConfigKey, ConfigKey, ConfigKey]:
    ai = ConfigKey("ai", AIConfiguration.from_mapping, required=True)
    knowledge = ConfigKey("knowledge", KnowledgeConfiguration.from_mapping)
    analysis = ConfigKey("dataAnalysis", DataAnalysisConfiguration.from_mapping)
    return ConfigCenter(keys=(ai, knowledge, analysis)), ai, knowledge, analysis


def test_config_center_merges_partial_sources_in_registration_order():
    center, ai_key, knowledge_key, analysis_key = _center()

    snapshot = center.initialize(
        (
            Source(
                "runtime.ini",
                {
                    "ai": {
                        "completion": {
                            "baseUrl": "https://model.example/v1",
                            "model": "chat-model",
                        },
                        "embedding": {"model": "embedding-model"},
                    },
                    "knowledge": {"nl2sql": {"indexName": "ini-index"}},
                },
            ),
            Source(
                "database",
                {
                    "ai": {
                        "completion": {"apiKey": "secret"},
                        "embedding": {"useCompletionAuth": True},
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

    assert center.get(ai_key).completion.api_key == "secret"
    assert center.get(ai_key).embedding.base_url == "https://model.example/v1"
    assert center.get(knowledge_key).nl2sql_index_name == "env-index"
    assert center.get(analysis_key).query_strategy == "ibis_planner"
    assert snapshot.sources["knowledge"]["nl2sql.indexName"] == "environment"


def test_config_center_snapshot_is_read_only_and_secret_repr_is_masked():
    center, ai_key, _knowledge, _analysis = _center()
    snapshot = center.initialize(
        (
            Source(
                "database",
                {
                    "ai": {
                        "completion": {
                            "baseUrl": "https://model.example/v1",
                            "model": "chat-model",
                            "apiKey": "top-secret",
                        },
                        "embedding": {
                            "model": "embedding-model",
                            "useCompletionAuth": True,
                        },
                    }
                },
            ),
        )
    )

    assert "top-secret" not in repr(center.get(ai_key))
    with pytest.raises(TypeError):
        snapshot.values["ai"] = object()


def test_config_center_rejects_missing_required_ai_configuration():
    center, _ai, _knowledge, _analysis = _center()

    with pytest.raises(ValueError, match="AI completion configuration is incomplete"):
        center.initialize(())


def test_runtime_ini_source_maps_business_sections():
    class FakeIni:
        values = {
            "chatbi.ai.completion": [
                ("base_url", "https://model.example/v1"),
                ("temperature", "0.4"),
            ],
            "chatbi.knowledge.nl2sql": [("index_name", "network-index")],
            "chatbi.data_analysis": [("query_strategy", "ibis_planner")],
        }

        def items(self, section):
            return self.values.get(section, ())

    payload = RuntimeIniConfigSource(ini=FakeIni()).load()

    assert payload["ai"]["completion"]["baseUrl"] == "https://model.example/v1"
    assert payload["ai"]["completion"]["temperature"] == 0.4
    assert payload["knowledge"]["nl2sql"]["indexName"] == "network-index"
    assert payload["dataAnalysis"]["queryStrategy"] == "ibis_planner"


def test_nodeagent_source_ignores_platform_external_services():
    class Client:
        def get_json(self, **_kwargs):
            return {
                "externalServices": {"onequery": {"baseUrl": "https://ignored"}},
                "chatbi": {
                    "knowledge": {
                        "nl2sql": {"indexName": "network-index"},
                    }
                },
            }

    payload = NodeAgentAppConfigSource(client=Client()).load()

    assert payload == {
        "knowledge": {
            "nl2sql": {"indexName": "network-index"},
        }
    }
    assert "externalServices" not in payload


def test_environment_source_only_exposes_chatbi_business_compatibility(monkeypatch):
    monkeypatch.setenv("REPORT_QUERY_STRATEGY", "ibis_planner")
    monkeypatch.setenv("CHATBI_COMPLETION_MODEL", "chat-model")

    payload = EnvironmentConfigSource().load()

    assert payload["dataAnalysis"]["queryStrategy"] == "ibis_planner"
    assert payload["ai"]["completion"]["model"] == "chat-model"
