from __future__ import annotations

import pytest

from src.contexts.conversation.application.ports import GuardrailResult
from src.contexts.data_analysis.application.services import DATA_ANALYSIS_INSTRUCTION, DataAnalysisService
from src.contexts.data_analysis.domain.models import DatasetColumn, DatasetResult
from src.shared.agentflow import FlowEdge, FlowGraph, FlowNode, InMemoryFlowRuntime, SubflowRegistry
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


def test_data_analysis_generates_guarded_sql_and_bi_visualizations():
    service, query = _service()

    answer = service.analyze_from_natural_language(question="查询核心设备健康评分", user_id="default")

    assert answer.query_spec.sql == "select device_name, health_score from network_health"
    assert query.calls[0]["context"] == {"lineage.tracing.enable": True, "scenario": DATA_ANALYSIS_INSTRUCTION}
    assert answer.summary == "核心设备整体稳定，建议关注出口路由器-B。"
    assert [item["type"] for item in answer.components] == ["chart", "table"]
    assert answer.components[0]["dataProperties"]["chartType"] == "bar"


def test_data_analysis_stops_before_execution_when_application_guardrail_blocks_sql():
    service, query = _service(guardrail_passed=False)

    with pytest.raises(ValidationError, match="SQL blocked"):
        service.analyze_from_natural_language(question="查询核心设备健康评分", user_id="default")

    assert query.calls == []


def test_data_analysis_flow_runs_nl2data_parallel_branches_and_finalizes():
    service, _query = _service()

    events = InMemoryFlowRuntime(max_workers=4).run_sync(
        service.create_natural_language_flow(question="查询核心设备健康评分", user_id="default")
    )

    step_codes = [event.step.code for event in events if event.step is not None and event.step.status == "finished"]
    assert "data_analysis.nl2sql" in step_codes
    assert "data_analysis.sql2data" in step_codes
    assert "data_analysis.data2chart" in step_codes
    assert "data_analysis.data2summary" in step_codes
    assert step_codes[-1] == "data_analysis.finalize"
    answer_event = next(event for event in events if event.event_type == "answer")
    assert answer_event.answer["answerType"] == "DATA_ANALYSIS"
    assert answer_event.answer["answer"]["sql"] == "select device_name, health_score from network_health"


def test_data_analysis_sql_entry_flow_starts_from_sql2data():
    service, query = _service()

    events = InMemoryFlowRuntime(max_workers=4).run_sync(
        service.create_sql_flow(
            sql="select device_name, health_score from network_health",
            question="查询核心设备健康评分",
            user_id="default",
        )
    )

    step_codes = [event.step.code for event in events if event.step is not None and event.step.status == "finished"]
    assert "data_analysis.nl2sql" not in step_codes
    assert step_codes[0] == "data_analysis.sql2data"
    assert query.calls[0]["query"] == "select device_name, health_score from network_health"
    assert next(event for event in events if event.event_type == "answer").answer["answerType"] == "DATA_ANALYSIS"


def test_data_analysis_subflow_registry_exposes_nl2data_for_parent_flows():
    service, _query = _service()

    graph = FlowGraph(start="parent_start")

    def call_child(context):
        answer = context.call_subflow(
            "data_analysis.nl2data",
            {"question": "查询核心设备健康评分", "userId": "default"},
            alias="child_nl2data",
        )
        context.set_state("child_answer", answer)

    def finalize(context):
        context.emit_answer({"answerType": "PARENT", "answer": {"child": context.get_state("child_answer")}})

    graph.add_node(FlowNode(id="parent_start", title="调用智能问数子流程", handler=call_child))
    graph.add_node(FlowNode(id="parent_finalize", title="完成父流程", handler=finalize))
    graph.add_edge(FlowEdge(source="parent_start", target="parent_finalize"))

    events = InMemoryFlowRuntime(subflow_registry=SubflowRegistry(service.subflow_specs())).run_sync(graph)

    assert any(event.source_subflow and event.source_subflow["alias"] == "child_nl2data" for event in events)
    parent_answer = next(event.answer for event in events if event.event_type == "answer" and event.answer["answerType"] == "PARENT")
    assert parent_answer["answer"]["child"]["answerType"] == "DATA_ANALYSIS_STEP"
    assert parent_answer["answer"]["child"]["answer"]["querySpec"]["sql"] == "select device_name, health_score from network_health"
