from __future__ import annotations

import pytest

from src.contexts.conversation.application.ports import GuardrailResult
from src.contexts.data_analysis.application.services import DataAnalysisService
from src.contexts.data_analysis.domain.models import DatasetColumn, DatasetResult
from src.shared.kernel.errors import ValidationError


class _AiGateway:
    def __init__(self) -> None:
        self.calls = 0

    def chat_completion(self, *_args, **_kwargs):
        self.calls += 1
        if self.calls == 1:
            return {
                "content": (
                    '{"intent":"查询核心设备健康评分","sql":"select device_name, health_score from network_health",'
                    '"entities":["network_health"],"dimensions":["device_name"],"measures":["health_score"]}'
                )
            }
        return {"content": "核心设备整体稳定，建议关注出口路由器-B。"}


class _QueryService:
    def __init__(self) -> None:
        self.calls = []

    def execute_sql(self, **kwargs):
        self.calls.append(kwargs)
        return DatasetResult(
            columns=[
                DatasetColumn(key="device_name", metadata={"type": "string"}),
                DatasetColumn(key="health_score", metadata={"type": "double"}),
            ],
            rows=[
                {"device_name": "核心交换机-A", "health_score": 98.5},
                {"device_name": "出口路由器-B", "health_score": 82.0},
            ],
        )


class _CatalogGateway:
    def list_logical_entities(self, *, user_id: str):
        return [{"name": "network_health"}]


class _KnowledgeGateway:
    def retrieve_multi_index(self, *, query: str, user_id: str):
        return [{"sql": "select device_name, health_score from network_health"}]


class _GuardrailGateway:
    def __init__(self, *, passed: bool = True) -> None:
        self.passed = passed

    def check_application_security(self, *, kind: str, content: str, user_id: str):
        return GuardrailResult(passed=self.passed, reason="SQL blocked" if not self.passed else "")


def _service(*, guardrail_passed: bool = True):
    query = _QueryService()
    return (
        DataAnalysisService(
            query_service=query,
            data_catalog_gateway=_CatalogGateway(),
            knowledge_gateway=_KnowledgeGateway(),
            guardrail_gateway=_GuardrailGateway(passed=guardrail_passed),
            ai_gateway=_AiGateway(),
            completion_config_builder=lambda: object(),
        ),
        query,
    )


def test_query_data_generates_guarded_sql_and_bi_visualizations():
    service, query = _service()

    answer = service.query_data(question="查询核心设备健康评分", user_id="default")

    assert answer.query_spec.sql == "select device_name, health_score from network_health"
    assert query.calls[0]["context"] == {"lineage.tracing.enable": True, "scenario": "query_data"}
    assert answer.summary == "核心设备整体稳定，建议关注出口路由器-B。"
    assert [item["type"] for item in answer.components] == ["chart", "table"]
    assert answer.components[0]["dataProperties"]["chartType"] == "bar"


def test_query_data_stops_before_execution_when_application_guardrail_blocks_sql():
    service, query = _service(guardrail_passed=False)

    with pytest.raises(ValidationError, match="SQL blocked"):
        service.query_data(question="查询核心设备健康评分", user_id="default")

    assert query.calls == []
