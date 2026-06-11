from __future__ import annotations

import os
from typing import Any, Mapping

from runtime.config import Ini

from ...shared.configuration import ConfigSource
from ..persistence.dev_database import DevSessionLocal
from ..persistence.dev_models import SystemSetting
from ..platform.client import RuntimeHttpClient


class RuntimeIniConfigSource(ConfigSource):
    name = "runtime.ini"

    def __init__(self, *, ini: Ini | None = None) -> None:
        self.ini = ini or Ini()

    def load(self) -> Mapping[str, Mapping[str, Any]]:
        return {
            "ai": {
                "completion": _section(self.ini, "chatbi.ai.completion"),
                "embedding": _section(self.ini, "chatbi.ai.embedding"),
            },
            "knowledge": {
                **_section(self.ini, "chatbi.knowledge"),
                "nl2sql": _section(self.ini, "chatbi.knowledge.nl2sql"),
            },
            "dataAnalysis": _section(self.ini, "chatbi.data_analysis"),
        }


class NodeAgentAppConfigSource(ConfigSource):
    name = "nodeagent.appconf"

    def __init__(self, *, client: RuntimeHttpClient | None = None) -> None:
        self.client = client or RuntimeHttpClient()

    def load(self) -> Mapping[str, Mapping[str, Any]]:
        payload = self.client.get_json(
            path_or_url="/rest/nodeagent/v2/csi/appconf",
            params={"watch": "false"},
        )
        root = payload.get("chatbi") if isinstance(payload.get("chatbi"), dict) else payload
        return {
            key: value
            for key, value in {
                "ai": root.get("ai"),
                "knowledge": root.get("knowledge"),
                "dataAnalysis": root.get("dataAnalysis", root.get("data_analysis")),
            }.items()
            if isinstance(value, dict)
        }


class DatabaseConfigSource(ConfigSource):
    name = "database.system_settings"

    def load(self) -> Mapping[str, Mapping[str, Any]]:
        with DevSessionLocal() as session:
            row = session.query(SystemSetting).filter(SystemSetting.id == "global").first()
            if row is None:
                return {}
            return {
                "ai": {
                    "completion": dict(row.completion_config or {}),
                    "embedding": dict(row.embedding_config or {}),
                }
            }


class EnvironmentConfigSource(ConfigSource):
    name = "environment.compatibility"

    def load(self) -> Mapping[str, Mapping[str, Any]]:
        strategy = str(os.getenv("REPORT_QUERY_STRATEGY") or "").strip()
        completion = _environment_provider("CHATBI_COMPLETION")
        embedding = _environment_provider("CHATBI_EMBEDDING")
        result: dict[str, Mapping[str, Any]] = {}
        if strategy:
            result["dataAnalysis"] = {"queryStrategy": strategy}
        if completion or embedding:
            result["ai"] = {"completion": completion, "embedding": embedding}
        return result


def _section(ini: Ini, name: str) -> dict[str, Any]:
    return {_camelize(key): _coerce(value) for key, value in ini.items(name)}


def _camelize(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in tail)


def _coerce(value: str) -> Any:
    normalized = value.strip()
    lowered = normalized.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(normalized)
    except ValueError:
        pass
    try:
        return float(normalized)
    except ValueError:
        return normalized


def _environment_provider(prefix: str) -> dict[str, Any]:
    names = {
        "baseUrl": f"{prefix}_BASE_URL",
        "model": f"{prefix}_MODEL",
        "apiKey": f"{prefix}_API_KEY",
        "temperature": f"{prefix}_TEMPERATURE",
        "timeoutSeconds": f"{prefix}_TIMEOUT_SECONDS",
        "useCompletionAuth": f"{prefix}_USE_COMPLETION_AUTH",
    }
    return {
        key: _coerce(value)
        for key, env_name in names.items()
        if (value := str(os.getenv(env_name) or "").strip())
    }
