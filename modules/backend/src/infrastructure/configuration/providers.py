"""Provider-specific projections of the ConfigCenter snapshot."""

from __future__ import annotations

from ..ai.openai_compat import ProviderConfig
from .runtime import get_ai_configuration


def build_completion_provider_config() -> ProviderConfig:
    completion = get_ai_configuration().completion
    return ProviderConfig(
        base_url=completion.base_url,
        model=completion.model,
        api_key=completion.api_key,
        timeout_sec=completion.timeout_seconds,
        temperature=completion.temperature,
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
