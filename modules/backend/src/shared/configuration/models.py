from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


def _text(value: object, default: str = "") -> str:
    return str(value if value is not None else default).strip()


def _integer(value: object, default: int, *, minimum: int = 1) -> int:
    try:
        return max(minimum, int(value))
    except (TypeError, ValueError):
        return default


def _number(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _boolean(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


@dataclass(frozen=True, slots=True)
class CompletionConfiguration:
    base_url: str
    model: str
    api_key: str = field(repr=False)
    temperature: float = 0.2
    timeout_seconds: int = 60

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CompletionConfiguration":
        return cls(
            base_url=_text(value.get("baseUrl", value.get("base_url"))),
            model=_text(value.get("model")),
            api_key=_text(value.get("apiKey", value.get("api_key"))),
            temperature=_number(value.get("temperature"), 0.2),
            timeout_seconds=_integer(value.get("timeoutSeconds", value.get("timeout_sec")), 60),
        )


@dataclass(frozen=True, slots=True)
class EmbeddingConfiguration:
    base_url: str
    model: str
    api_key: str = field(repr=False)
    timeout_seconds: int = 60
    use_completion_auth: bool = True

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EmbeddingConfiguration":
        return cls(
            base_url=_text(value.get("baseUrl", value.get("base_url"))),
            model=_text(value.get("model")),
            api_key=_text(value.get("apiKey", value.get("api_key"))),
            timeout_seconds=_integer(value.get("timeoutSeconds", value.get("timeout_sec")), 60),
            use_completion_auth=_boolean(
                value.get("useCompletionAuth", value.get("use_completion_auth")),
                True,
            ),
        )


@dataclass(frozen=True, slots=True)
class AIConfiguration:
    completion: CompletionConfiguration
    embedding: EmbeddingConfiguration

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AIConfiguration":
        completion = CompletionConfiguration.from_mapping(_mapping(value.get("completion")))
        embedding = EmbeddingConfiguration.from_mapping(_mapping(value.get("embedding")))
        if not completion.base_url or not completion.model or not completion.api_key:
            raise ValueError("AI completion configuration is incomplete")
        if not embedding.model:
            raise ValueError("AI embedding model is required")
        if embedding.use_completion_auth:
            embedding = EmbeddingConfiguration(
                base_url=completion.base_url,
                model=embedding.model,
                api_key=completion.api_key,
                timeout_seconds=embedding.timeout_seconds,
                use_completion_auth=True,
            )
        elif not embedding.base_url or not embedding.api_key:
            raise ValueError("AI embedding configuration is incomplete")
        return cls(completion=completion, embedding=embedding)


@dataclass(frozen=True, slots=True)
class KnowledgeConfiguration:
    nl2sql_index_name: str = "nl2sql_cache"
    es_top_n: int = 5
    vs_top_n: int = 5
    rank_top_n: int = 3
    score_threshold: float = 0.5
    enable_hybrid_results: bool = True

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "KnowledgeConfiguration":
        nl2sql = _mapping(value.get("nl2sql"))
        return cls(
            nl2sql_index_name=_text(
                nl2sql.get("indexName", nl2sql.get("index_name")),
                "nl2sql_cache",
            )
            or "nl2sql_cache",
            es_top_n=_integer(nl2sql.get("esTopN", nl2sql.get("es_top_n")), 5),
            vs_top_n=_integer(nl2sql.get("vsTopN", nl2sql.get("vs_top_n")), 5),
            rank_top_n=_integer(value.get("rankTopN", value.get("rank_top_n")), 3),
            score_threshold=_number(
                value.get("scoreThreshold", value.get("score_threshold")),
                0.5,
            ),
            enable_hybrid_results=_boolean(
                value.get("enableHybridResults", value.get("enable_hybrid_results")),
                True,
            ),
        )


@dataclass(frozen=True, slots=True)
class DataAnalysisConfiguration:
    query_strategy: str = "single_pass"

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "DataAnalysisConfiguration":
        return cls(
            query_strategy=_text(
                value.get("queryStrategy", value.get("query_strategy")),
                "single_pass",
            )
            or "single_pass"
        )


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
