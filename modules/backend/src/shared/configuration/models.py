from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
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
    embedding: EmbeddingConfiguration

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AIConfiguration":
        embedding = EmbeddingConfiguration.from_mapping(_mapping(value.get("embedding")))
        if not embedding.model or not embedding.base_url or not embedding.api_key:
            raise ValueError("AI embedding configuration is incomplete")
        return cls(embedding=embedding)


@dataclass(frozen=True, slots=True)
class CandidateLLMConfiguration:
    name: str
    model_name: str = ""
    base_url: str = ""
    infer_params: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({})
    )

    @classmethod
    def from_mapping(
        cls,
        name: str,
        value: Mapping[str, Any],
        *,
        default_infer_params: Mapping[str, Any],
    ) -> "CandidateLLMConfiguration":
        infer_params = dict(default_infer_params)
        infer_params.update(_mapping(value.get("inferParams", value.get("infer_params"))))
        return cls(
            name=name,
            model_name=_text(value.get("modelName", value.get("model_name"))),
            base_url=_text(value.get("baseUrl", value.get("base_url"))),
            infer_params=MappingProxyType(infer_params),
        )

    def require_usable(self) -> "CandidateLLMConfiguration":
        if not self.model_name or not self.base_url:
            raise ValueError(f"LLM candidate configuration is incomplete: {self.name}")
        return self


@dataclass(frozen=True, slots=True)
class LLMConfiguration:
    default_llm: str
    infer_params: Mapping[str, Any]
    candidate_llms: Mapping[str, CandidateLLMConfiguration]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "LLMConfiguration":
        default_llm = _text(value.get("defaultLlm", value.get("default_llm")))
        default_infer_params = dict(
            _mapping(value.get("inferParams", value.get("infer_params")))
        )
        raw_candidates = _mapping(
            value.get("candidateLlms", value.get("candidate_llms"))
        )
        candidates = {
            str(name): CandidateLLMConfiguration.from_mapping(
                str(name),
                _mapping(candidate),
                default_infer_params=default_infer_params,
            )
            for name, candidate in raw_candidates.items()
            if isinstance(candidate, Mapping)
        }
        if not default_llm:
            raise ValueError("LLM default candidate is required")
        if default_llm not in candidates:
            raise ValueError(f"LLM default candidate does not exist: {default_llm}")
        return cls(
            default_llm=default_llm,
            infer_params=MappingProxyType(default_infer_params),
            candidate_llms=MappingProxyType(candidates),
        )

    def resolve(
        self,
        name: str | None = None,
        *,
        infer_params: Mapping[str, Any] | None = None,
    ) -> CandidateLLMConfiguration:
        candidate_name = name or self.default_llm
        candidate = self.candidate_llms.get(candidate_name)
        if candidate is None:
            raise ValueError(f"LLM candidate does not exist: {candidate_name}")
        candidate.require_usable()
        if not infer_params:
            return candidate
        merged = dict(candidate.infer_params)
        merged.update(infer_params)
        return CandidateLLMConfiguration(
            name=candidate.name,
            model_name=candidate.model_name,
            base_url=candidate.base_url,
            infer_params=MappingProxyType(merged),
        )


@dataclass(frozen=True, slots=True)
class KnowledgeIndexConfiguration:
    chatbi_klg_nl2chart_cus_global: str = ""
    chatbi_klg_nl2chart_cus_custom: str = ""
    chatbi_sql_few_shot: str = ""
    chatbi_klg_report_template: str = ""

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "KnowledgeIndexConfiguration":
        return cls(
            chatbi_klg_nl2chart_cus_global=_text(
                value.get(
                    "chatbiKlgNl2chartCusGlobal",
                    value.get("chatbi_klg_nl2chart_cus_global"),
                )
            ),
            chatbi_klg_nl2chart_cus_custom=_text(
                value.get(
                    "chatbiKlgNl2chartCusCustom",
                    value.get("chatbi_klg_nl2chart_cus_custom"),
                )
            ),
            chatbi_sql_few_shot=_text(
                value.get(
                    "chatbiSqlFewShot",
                    value.get("chatbi_sql_few_shot"),
                )
            ),
            chatbi_klg_report_template=_text(
                value.get(
                    "chatbiKlgReportTemplate",
                    value.get("chatbi_klg_report_template"),
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class KnowledgeConfiguration:
    index: KnowledgeIndexConfiguration = field(default_factory=KnowledgeIndexConfiguration)
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
            index=KnowledgeIndexConfiguration.from_mapping(_mapping(value.get("index"))),
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
