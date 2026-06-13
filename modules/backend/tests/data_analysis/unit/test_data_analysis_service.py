from __future__ import annotations

import pytest

from src.contexts.conversation.application.ports import GuardrailResult
from src.contexts.data_analysis.application.services import DATA_ANALYSIS_INSTRUCTION, DataAnalysisService
from src.contexts.data_analysis.domain.models import (
    Data2ChartInput,
    Data2SummaryInput,
    DatasetColumn,
    DatasetResult,
    Nl2SqlInput,
    Nl2SqlCompileError,
    QueryResult,
    Sql2DataInput,
)
from src.shared.agentflow import FlowEdge, FlowGraph, FlowNode, InMemoryFlowRuntime, SubflowRegistry
from src.shared.agentflow.metrics import FlowMetricsCollector, use_metrics_collector
from src.shared.kernel.errors import ErrorCode, UpstreamError, ValidationError
from src.infrastructure.prompts import get_prompt_catalog


class _AiGateway:
    def chat_completion(self, _config, messages, **_kwargs):
        prompt = messages[0]["content"]
        if "Ibis Key API Functions" in prompt:
            return {
                "content": '{"implementation":"def query(config):\\n    return config.network_health"}'
            }
        if "选择最合适的可视化类型" in prompt:
            return {
                "content": (
                    "title: 核心设备健康评分\n"
                    "type: Bar\n"
                    "summaries: []\n"
                    "series:\n"
                    "  - name: 健康评分\n"
                    "    type: Bar\n"
                    "    ex: device_name\n"
                    "    ey: health_score\n"
                )
            }
        if "sql_explanation" in prompt:
            return {
                "content": (
                    "title: 核心设备健康评分\n"
                    "sql_explanation: 按设备展示健康评分并关注低分设备。\n"
                    "summaries:\n"
                    "  - 核心设备整体稳定，建议关注出口路由器-B。\n"
                )
            }
        raise AssertionError(f"unexpected prompt: {prompt[:80]}")


class _QueryService:
    def __init__(self) -> None:
        self.calls = []

    def execute_sql_result(self, **kwargs):
        self.calls.append(kwargs)
        return QueryResult(
            ret_code=0,
            ret_info="",
            data=DatasetResult(
                columns=[
                    DatasetColumn(key="device_name", metadata={"type": "string"}),
                    DatasetColumn(key="health_score", metadata={"type": "double"}),
                ],
                rows=[
                    {"device_name": "核心交换机-A", "health_score": 98.5},
                    {"device_name": "出口路由器-B", "health_score": 82.0},
                ],
            ),
        )


class _CatalogGateway:
    def __init__(self) -> None:
        self.detail_calls = []

    def list_logical_entities(self, *, user_id: str):
        return [{"name": "network_health"}]

    def get_logical_entity(self, *, name: str, user_id: str):
        self.detail_calls.append((name, user_id))
        return _logical_entity(name)

    def list_logical_relations(self, *, user_id: str):
        return []


class _KnowledgeGateway:
    def retrieve_multi_index(self, *, query: str, user_id: str):
        return [{"sql": "select device_name, health_score from network_health"}]

    def retrieve_sql_few_shot(self, *, query: str, user_id: str):
        return [{"sql": "select device_name, health_score from network_health"}]


class _Nl2SqlCompiler:
    def __init__(self, failures: int = 0) -> None:
        self.calls = []
        self.failures = failures

    def compile(self, *, source, context):
        self.calls.append((source, context))
        if len(self.calls) <= self.failures:
            raise Nl2SqlCompileError("compile", "temporary compile failure")
        return "select device_name, health_score from network_health"


class _GuardrailGateway:
    def __init__(self, *, passed: bool = True) -> None:
        self.passed = passed

    def check_application_security(self, *, kind: str, content: str, user_id: str):
        return GuardrailResult(passed=self.passed, reason="SQL blocked" if not self.passed else "")


class _LogicalEntityValidator:
    def validate(self, *, entity, expected_name):
        assert entity["name"] == expected_name
        return entity


def _logical_entity(name: str, *, extra_fields=None):
    fields = [
        {
            "name": "device_name",
            "businessName": "Device name",
            "businessName_cn": "设备名称",
            "description": "Device name",
            "description_cn": "设备名称",
            "columnType": "dimension",
            "type": {"name": "device_name", "type": "string"},
        },
        {
            "name": "health_score",
            "businessName": "Health score",
            "businessName_cn": "健康评分",
            "description": "Health score",
            "description_cn": "健康评分",
            "columnType": "measure",
            "type": {"name": "health_score", "type": "double"},
        },
        *(extra_fields or []),
    ]
    return {
        "name": name,
        "businessName": "Network health",
        "businessName_cn": "网络健康",
        "description": "Network health data",
        "description_cn": "网络健康数据",
        "schema": {"name": "root", "type": "record", "fields": fields},
    }


def _service(*, guardrail_passed: bool = True, query_service=None, compiler=None):
    query = query_service or _QueryService()
    return (
        DataAnalysisService(
            query_service=query,
            data_catalog_gateway=_CatalogGateway(),
            knowledge_gateway=_KnowledgeGateway(),
            guardrail_gateway=_GuardrailGateway(passed=guardrail_passed),
            ai_gateway=_AiGateway(),
            completion_config_builder=lambda: object(),
            prompt_catalog=get_prompt_catalog(),
            nl2sql_compiler=compiler or _Nl2SqlCompiler(),
            logical_entity_validator=_LogicalEntityValidator(),
        ),
        query,
    )


def test_data_analysis_generates_guarded_sql_and_bi_visualizations():
    service, query = _service()

    answer = service.analyze_from_natural_language(question="查询核心设备健康评分", user_id="default")

    assert answer.query_spec.sql == "select device_name, health_score from network_health"
    assert query.calls[0]["context"] == {"lineage.tracing.enable": True, "scenario": DATA_ANALYSIS_INSTRUCTION}
    assert answer.summary == "核心设备整体稳定，建议关注出口路由器-B。"
    assert answer.title == "核心设备健康评分"
    assert answer.sql_explanation == "按设备展示健康评分并关注低分设备。"
    assert [item["type"] for item in answer.components] == ["chart", "table"]
    assert answer.components[0]["dataProperties"]["chartType"] == "bar"


def test_data_analysis_step_contracts_share_complete_query_result():
    service, _query = _service()

    generated = service.nl2sql(value=Nl2SqlInput(question="查询核心设备健康评分"), user_id="default")
    query_result = service.sql2data(
        value=Sql2DataInput(question="查询核心设备健康评分", sql=generated.sql),
        user_id="default",
    )
    chart = service.data2chart(value=Data2ChartInput(question="查询核心设备健康评分", query_result=query_result))
    summary = service.data2summary(
        value=Data2SummaryInput(question="查询核心设备健康评分", sql=generated.sql, query_result=query_result)
    )

    assert generated.sql == "select device_name, health_score from network_health"
    assert query_result.ret_code == 0
    assert chart.type == "bar"
    assert chart.title == "核心设备健康评分"
    assert chart.series == [{"name": "健康评分", "type": "bar", "ex": "device_name", "ey": "health_score"}]
    assert chart.query_result is query_result
    assert summary.summaries == ["核心设备整体稳定，建议关注出口路由器-B。"]
    assert summary.sql_explanation == "按设备展示健康评分并关注低分设备。"


def test_nl2sql_retries_generated_ibis_compilation_up_to_three_attempts():
    compiler = _Nl2SqlCompiler(failures=2)
    service, _query = _service(compiler=compiler)

    generated = service.nl2sql(value=Nl2SqlInput(question="查询核心设备健康评分"), user_id="default")

    assert generated.sql == "select device_name, health_score from network_health"
    assert len(compiler.calls) == 3
    assert compiler.calls[0][1].entities[0]["name"] == "network_health"


def test_nl2sql_uses_selected_entity_detail_and_never_falls_back_to_summary():
    class InvalidDetailCatalog(_CatalogGateway):
        def get_logical_entity(self, *, name: str, user_id: str):
            raise UpstreamError("detail unavailable", error_code=ErrorCode.DATA_ANALYSIS_METADATA_INVALID)

    service, _query = _service()
    service.data_catalog_gateway = InvalidDetailCatalog()

    with pytest.raises(UpstreamError, match="detail unavailable"):
        service.nl2sql(value=Nl2SqlInput(question="查询核心设备健康评分"), user_id="user-a")


def test_nl2sql_requests_only_selected_details_and_counts_valid_participants():
    class ManyEntitiesCatalog(_CatalogGateway):
        def list_logical_entities(self, *, user_id: str):
            return [{"name": f"entity_{index}"} for index in range(10)]

    service, _query = _service()
    catalog = ManyEntitiesCatalog()
    service.data_catalog_gateway = catalog
    collector = FlowMetricsCollector()

    with use_metrics_collector(collector):
        context = service._build_nl2sql_context(question="查询网络数据", user_id="user-a")

    assert len(context.entities) == 8
    assert catalog.detail_calls == [(f"entity_{index}", "user-a") for index in range(8)]
    metrics = collector.snapshot(run_id="run_1", status="finished")
    assert metrics.unique_counts["datacatalog.logical_entity.used"] == 8


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
    assert parent_answer["answer"]["child"]["answer"]["sql"] == "select device_name, health_score from network_health"
    assert parent_answer["answer"]["child"]["answer"]["query_result"]["retCode"] == 0


def test_known_onequery_error_stops_chart_summary_and_finalize_nodes():
    class FailingQueryService:
        def execute_sql_result(self, **_kwargs):
            raise UpstreamError(
                "查询引用的字段不存在。",
                error_code=ErrorCode.DATA_ANALYSIS_QUERY_FIELD_NOT_FOUND,
                retryable=False,
                details={"retCode": "04023", "upstreamCode": "04023"},
            )

    service, _query = _service(query_service=FailingQueryService())

    events = InMemoryFlowRuntime(max_workers=4).run_sync(
        service.create_natural_language_flow(question="查询不存在的字段", user_id="default")
    )

    finished = {event.step.code for event in events if event.step is not None and event.step.status == "finished"}
    assert "data_analysis.nl2sql" in finished
    assert "data_analysis.data2chart" not in finished
    assert "data_analysis.data2summary" not in finished
    assert "data_analysis.finalize" not in finished
    error_event = next(event for event in events if event.event_type == "error")
    assert error_event.error["errorCode"] == ErrorCode.DATA_ANALYSIS_QUERY_FIELD_NOT_FOUND
    assert error_event.error["retryable"] is False
