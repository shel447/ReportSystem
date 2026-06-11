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
        completion = _section(self.ini, "chatbi.ai.completion")
        embedding = _with_completion_auth(
            _section(self.ini, "chatbi.ai.embedding"),
            completion,
        )
        return {
            "ai": {"embedding": embedding},
            "llm": _runtime_ini_llm(self.ini, legacy_completion=completion),
            "knowledge": {
                **_section(self.ini, "chatbi.knowledge"),
                "nl2sql": _section(self.ini, "chatbi.knowledge.nl2sql"),
                "index": _section(self.ini, "chatbi.knowledge.index"),
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
                "llm": root.get("llm"),
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
            completion = dict(row.completion_config or {})
            embedding = _with_completion_auth(
                dict(row.embedding_config or {}),
                completion,
            )
            return {
                "ai": {"embedding": embedding},
                "llm": _legacy_completion_llm(completion, "database_completion"),
            }


class EnvironmentConfigSource(ConfigSource):
    name = "environment.compatibility"

    def load(self) -> Mapping[str, Mapping[str, Any]]:
        strategy = str(os.getenv("REPORT_QUERY_STRATEGY") or "").strip()
        completion = _environment_provider("CHATBI_COMPLETION")
        embedding = _environment_provider("CHATBI_EMBEDDING")
        llm = _environment_llm() or _legacy_completion_llm(
            completion,
            "environment_completion",
        )
        knowledge_indexes = {
            key: value
            for key, env_name in {
                "chatbi_klg_nl2chart_cus_global": "CHATBI_KLG_NL2CHART_CUS_GLOBAL",
                "chatbi_klg_nl2chart_cus_custom": "CHATBI_KLG_NL2CHART_CUS_CUSTOM",
                "chatbi_sql_few_shot": "CHATBI_SQL_FEW_SHOT",
                "chatbi_klg_report_template": "CHATBI_KLG_REPORT_TEMPLATE",
            }.items()
            if (value := str(os.getenv(env_name) or "").strip())
        }
        result: dict[str, Mapping[str, Any]] = {}
        if strategy:
            result["dataAnalysis"] = {"queryStrategy": strategy}
        if completion or embedding:
            result["ai"] = {
                "embedding": _with_completion_auth(embedding, completion)
            }
        if llm:
            result["llm"] = llm
        if knowledge_indexes:
            result["knowledge"] = {"index": knowledge_indexes}
        return result


def _environment_llm() -> dict[str, Any]:
    candidate_name = str(os.getenv("CHATBI_LLM_DEFAULT_LLM") or "").strip()
    model_name = str(os.getenv("CHATBI_LLM_MODEL_NAME") or "").strip()
    base_url = str(os.getenv("CHATBI_LLM_BASE_URL") or "").strip()
    if not candidate_name and not model_name and not base_url:
        return {}
    candidate_name = candidate_name or "default"
    stream_value = str(os.getenv("CHATBI_LLM_STREAM") or "").strip()
    infer_params = {"stream": _coerce(stream_value)} if stream_value else {}
    return {
        "defaultLlm": candidate_name,
        "inferParams": infer_params,
        "candidateLlms": {
            candidate_name: {
                "modelName": model_name,
                "baseUrl": base_url,
            }
        },
    }


def _runtime_ini_llm(
    ini: Ini,
    *,
    legacy_completion: Mapping[str, Any],
) -> dict[str, Any]:
    llm = _section(ini, "chatbi.llm")
    infer_params = _section(ini, "chatbi.llm.infer_params")
    candidates: dict[str, Any] = {}
    sections = ini.sections() if hasattr(ini, "sections") else ()
    prefix = "chatbi.llm.candidate_llms."
    for section in sections:
        if section.startswith(prefix) and not section.endswith(".infer_params"):
            name = section[len(prefix) :].strip()
            if name:
                candidate = _section(ini, section)
                candidate_infer_params = _section(ini, f"{section}.infer_params")
                if candidate_infer_params:
                    candidate["inferParams"] = candidate_infer_params
                candidates[name] = candidate
    if candidates:
        llm["candidateLlms"] = candidates
        if infer_params:
            llm["inferParams"] = infer_params
        return llm
    return _legacy_completion_llm(legacy_completion, "runtime_completion")


def _legacy_completion_llm(
    completion: Mapping[str, Any],
    candidate_name: str,
) -> dict[str, Any]:
    base_url = completion.get("baseUrl", completion.get("base_url"))
    model_name = completion.get(
        "modelName",
        completion.get("model_name", completion.get("model")),
    )
    if not base_url and not model_name:
        return {}
    infer_params: dict[str, Any] = {}
    if "temperature" in completion:
        infer_params["temperature"] = completion["temperature"]
    if "timeoutSeconds" in completion:
        infer_params["timeoutSeconds"] = completion["timeoutSeconds"]
    elif "timeout_sec" in completion:
        infer_params["timeoutSeconds"] = completion["timeout_sec"]
    return {
        "defaultLlm": candidate_name,
        "candidateLlms": {
            candidate_name: {
                "baseUrl": base_url or "",
                "modelName": model_name or "",
                "inferParams": infer_params,
            }
        },
    }


def _with_completion_auth(
    embedding: Mapping[str, Any],
    completion: Mapping[str, Any],
) -> dict[str, Any]:
    resolved = dict(embedding)
    use_completion_auth = _boolean_value(
        resolved.get("useCompletionAuth", resolved.get("use_completion_auth")),
        True,
    )
    if not use_completion_auth:
        return resolved
    resolved.setdefault("baseUrl", completion.get("baseUrl", completion.get("base_url")))
    resolved.setdefault("apiKey", completion.get("apiKey", completion.get("api_key")))
    return resolved


def _boolean_value(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return default


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
