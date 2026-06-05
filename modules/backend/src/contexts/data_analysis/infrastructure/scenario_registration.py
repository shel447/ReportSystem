"""Data-analysis scenario registration provider."""

from __future__ import annotations

from ...conversation.application.scenarios import (
    ScenarioAnswerProjection,
    ScenarioCodec,
    ScenarioHandler,
    ScenarioRegistration,
    ScenarioRegistrationProvider,
    ScenarioResult,
)
from ...conversation.domain.models import ScenarioInvocationContext
from ..domain.models import data_analysis_answer_to_dict


class DataAnalysisScenarioCodec(ScenarioCodec):
    def decode(self, *, context: ScenarioInvocationContext, payload: dict) -> ScenarioInvocationContext:
        return context


class DataAnalysisScenarioHandler(ScenarioHandler):
    def __init__(self, *, service) -> None:
        self.service = service

    def handle(self, *, command: object) -> ScenarioResult:
        if not isinstance(command, ScenarioInvocationContext):
            raise TypeError("data analysis scenario requires ScenarioInvocationContext")
        answer = self.service.query_data(question=str(command.question or ""), user_id=command.user_id)
        return ScenarioResult(
            status="finished",
            answer=ScenarioAnswerProjection(answer_type="DATA_ANALYSIS", payload=data_analysis_answer_to_dict(answer)),
        )


class DataAnalysisScenarioRegistrationProvider(ScenarioRegistrationProvider):
    def __init__(self, *, service) -> None:
        self.service = service

    def registration(self) -> ScenarioRegistration:
        return ScenarioRegistration(
            key="data_analysis",
            name="智能问数",
            description="通过自然语言查询业务数据并返回解释和图表",
            instructions={"query_data"},
            default_instruction="query_data",
            keywords={"查询", "统计", "多少", "趋势", "分布"},
            examples={"查询本月设备告警分布", "统计核心设备健康评分趋势"},
            supports_continuation=True,
            codec=DataAnalysisScenarioCodec(),
            handler=DataAnalysisScenarioHandler(service=self.service),
        )
