from __future__ import annotations

import logging

from ...shared.configuration import (
    AIConfiguration,
    ConfigCenter,
    ConfigKey,
    DataAnalysisConfiguration,
    KnowledgeConfiguration,
)
from .sources import (
    DatabaseConfigSource,
    EnvironmentConfigSource,
    NodeAgentAppConfigSource,
    RuntimeIniConfigSource,
)

LOGGER = logging.getLogger(__name__)

AI_CONFIG = ConfigKey("ai", AIConfiguration.from_mapping, required=True)
KNOWLEDGE_CONFIG = ConfigKey(
    "knowledge",
    KnowledgeConfiguration.from_mapping,
)
DATA_ANALYSIS_CONFIG = ConfigKey(
    "dataAnalysis",
    DataAnalysisConfiguration.from_mapping,
)

config_center = ConfigCenter(
    keys=(AI_CONFIG, KNOWLEDGE_CONFIG, DATA_ANALYSIS_CONFIG),
)


def initialize_config_center() -> None:
    snapshot = config_center.initialize(
        (
            RuntimeIniConfigSource(),
            NodeAgentAppConfigSource(),
            DatabaseConfigSource(),
            EnvironmentConfigSource(),
        )
    )
    for failure in snapshot.failures:
        LOGGER.warning("ChatBI configuration source failed: %s", failure)


def get_ai_configuration() -> AIConfiguration:
    return config_center.get(AI_CONFIG)


def get_knowledge_configuration() -> KnowledgeConfiguration:
    try:
        return config_center.get(KNOWLEDGE_CONFIG)
    except RuntimeError:
        return KnowledgeConfiguration()


def get_data_analysis_configuration() -> DataAnalysisConfiguration:
    try:
        return config_center.get(DATA_ANALYSIS_CONFIG)
    except RuntimeError:
        return DataAnalysisConfiguration()
