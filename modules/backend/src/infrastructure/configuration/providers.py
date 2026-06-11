"""Provider-specific projections of the ConfigCenter snapshot."""

from __future__ import annotations

from ..ai.openai_compat import ProviderConfig
from .runtime import get_ai_configuration, get_llm_configuration


def build_completion_provider_config() -> ProviderConfig:
    candidate = get_llm_configuration().resolve()
    infer_params = dict(candidate.infer_params)
    return ProviderConfig(
        base_url=candidate.base_url,
        model=candidate.model_name,
        timeout_sec=int(
            infer_params.pop(
                "timeoutSeconds",
                infer_params.pop("timeout_seconds", 60),
            )
        ),
        temperature=float(infer_params.get("temperature", 0.2)),
        infer_params=infer_params,
    )


def build_embedding_provider_config() -> ProviderConfig:
    embedding = get_ai_configuration().embedding
    return ProviderConfig(
        base_url=embedding.base_url,
        model=embedding.model,
        api_key=embedding.api_key,
        timeout_sec=embedding.timeout_seconds,
        temperature=0.0,
    )
