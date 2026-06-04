"""Data-analysis scenario registration provider for the conversation context."""

from __future__ import annotations

from ...conversation.application.scenarios import ScenarioAnswerProjection, ScenarioRegistration, ScenarioResult
from ...conversation.domain.models import ChatContext
from ..domain.models import data_analysis_answer_to_dict


class DataAnalysisScenarioCodec:
    def decode(self, *, context: ChatContext, payload: dict) -> ChatContext:
        return context


class DataAnalysisScenarioHandler:
    def __init__(self, *, service) -> None:
        self.service = service

    def handle(self, *, command: object) -> ScenarioResult:
        if not isinstance(command, ChatContext):
            raise TypeError("data analysis scenario requires ChatContext")
        answer = self.service.query_data(question=str(command.question or ""), user_id=command.user_id)
        return ScenarioResult(
            status="finished",
            answer=ScenarioAnswerProjection(answer_type="DATA_ANALYSIS", payload=data_analysis_answer_to_dict(answer)),
        )


class DataAnalysisScenarioRegistrationProvider:
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
