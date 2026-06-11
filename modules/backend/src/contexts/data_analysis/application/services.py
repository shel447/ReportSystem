"""Application orchestration for reusable data analysis and query execution."""

from __future__ import annotations

import ast
import json
from typing import Any

from ....shared.agentflow import FlowContext, FlowEdge, FlowGraph, FlowNode, SubflowEventPolicy, SubflowSpec
from ....shared.kernel.errors import ErrorCode, ValidationError
from ....shared.kernel.audit import AuditEvent, AuditPublisher
from ....shared.kernel.safety import GuardrailGateway
from ..domain.models import (
    Data2ChartInput,
    Data2ChartOutput,
    Data2SummaryInput,
    Data2SummaryOutput,
    DataAnalysisAnswer,
    DatasetResult,
    Nl2DataOutput,
    Nl2SqlInput,
    Nl2SqlOutput,
    QueryResult,
    QuerySpec,
    Sql2DataInput,
    data2chart_input_from_dict,
    data2chart_output_to_dict,
    data2summary_input_from_dict,
    data2summary_output_to_dict,
    data_analysis_answer_to_dict,
    nl2data_output_to_dict,
    nl2sql_input_from_dict,
    nl2sql_output_to_dict,
    query_result_to_dict,
    sql2data_input_from_dict,
)
from .ports import ApiDatasetGateway, DataCatalogGateway, KnowledgeGateway, OneQueryGateway


DATA_ANALYSIS_INSTRUCTION = "data_analysis"
NL2SQL_NODE = "data_analysis.nl2sql"
SQL2DATA_NODE = "data_analysis.sql2data"
DATA2CHART_NODE = "data_analysis.data2chart"
DATA2SUMMARY_NODE = "data_analysis.data2summary"
FINALIZE_NODE = "data_analysis.finalize"


class DataQueryService:
    """Shared SQL/API query execution used by reports and interactive analysis."""

    def __init__(self, *, onequery_gateway: OneQueryGateway, api_gateway: ApiDatasetGateway | None = None) -> None:
        self.onequery_gateway = onequery_gateway
        self.api_gateway = api_gateway

    def execute_sql(self, *, query: str, context: dict[str, Any], user_id: str) -> DatasetResult:
        return self.execute_sql_result(query=query, context=context, user_id=user_id).data

    def execute_sql_result(self, *, query: str, context: dict[str, Any], user_id: str) -> QueryResult:
        return self.onequery_gateway.execute(query=query, context=context, user_id=user_id)

    def execute_api(self, *, source: str, payload: dict[str, Any], user_id: str) -> DatasetResult:
        if self.api_gateway is None:
            raise ValidationError(
                "API dataset gateway is not configured",
                error_code=ErrorCode.DATA_ANALYSIS_DATASOURCE_UNAVAILABLE,
                category="capability",
            )
        return self.api_gateway.execute(source=source, payload=payload, user_id=user_id)


class DataAnalysisService:
    def __init__(
        self,
        *,
        query_service: DataQueryService,
        data_catalog_gateway: DataCatalogGateway,
        knowledge_gateway: KnowledgeGateway,
        guardrail_gateway: GuardrailGateway,
        ai_gateway,
        completion_config_builder,
        audit_publisher: AuditPublisher | None = None,
    ) -> None:
        self.query_service = query_service
        self.data_catalog_gateway = data_catalog_gateway
        self.knowledge_gateway = knowledge_gateway
        self.guardrail_gateway = guardrail_gateway
        self.ai_gateway = ai_gateway
        self.completion_config_builder = completion_config_builder
        self.audit_publisher = audit_publisher

    def analyze_from_natural_language(self, *, question: str, user_id: str) -> DataAnalysisAnswer:
        result = self.nl2data(value=Nl2SqlInput(question=question), user_id=user_id)
        chart = self.data2chart(value=Data2ChartInput(question=question, query_result=result.query_result))
        summary = self.data2summary(value=Data2SummaryInput(question=question, sql=result.sql, query_result=result.query_result))
        answer = self._build_answer(
            question=question,
            sql=result.sql,
            data=result.query_result.data,
            chart=chart,
            summary=summary,
        )
        self._audit_analysis_completed(answer=answer, user_id=user_id)
        return answer

    def analyze_from_sql(self, *, sql: str, question: str | None = None, user_id: str) -> DataAnalysisAnswer:
        sql_input = Sql2DataInput(question=str(question or "SQL 数据分析"), sql=str(sql or "").strip())
        if not sql_input.sql:
            raise ValidationError(
                "SQL must not be empty",
                error_code=ErrorCode.DATA_ANALYSIS_QUERY_GENERATION_FAILED,
            )
        query_result = self.sql2data(value=sql_input, user_id=user_id)
        chart = self.data2chart(value=Data2ChartInput(question=sql_input.question, query_result=query_result))
        summary = self.data2summary(value=Data2SummaryInput(question=sql_input.question, sql=sql_input.sql, query_result=query_result))
        answer = self._build_answer(
            question=sql_input.question,
            sql=sql_input.sql,
            data=query_result.data,
            chart=chart,
            summary=summary,
        )
        self._audit_analysis_completed(answer=answer, user_id=user_id)
        return answer

    def nl2data(self, *, value: Nl2SqlInput, user_id: str) -> Nl2DataOutput:
        generated = self.nl2sql(value=value, user_id=user_id)
        query_result = self.sql2data(value=Sql2DataInput(question=value.question, sql=generated.sql), user_id=user_id)
        return Nl2DataOutput(sql=generated.sql, intent_function=generated.intent_function, query_result=query_result)

    def nl2sql(self, *, value: Nl2SqlInput, user_id: str) -> Nl2SqlOutput:
        entities = self.data_catalog_gateway.list_logical_entities(user_id=user_id)
        try:
            retrieved = self.knowledge_gateway.retrieve_multi_index(query=value.question, user_id=user_id)
        except Exception:
            retrieved = []
        output = self._generate_nl2sql_output(question=value.question, entities=entities, retrieved=retrieved)
        security = self.guardrail_gateway.check_application_security(kind="nl2sql", content=output.sql, user_id=user_id)
        if not security.passed:
            self._audit(
                AuditEvent(
                    operation="data_analysis.guardrail.sql",
                    detail=security.reason or "generated SQL blocked",
                    user_id=user_id,
                    result="FAILED",
                    level="WARNING",
                    kind="security",
                )
            )
            raise ValidationError(
                security.reason or "生成查询未通过安全检查",
                error_code=ErrorCode.DATA_ANALYSIS_QUERY_BLOCKED,
                category="safety",
            )
        return output

    def sql2data(self, *, value: Sql2DataInput, user_id: str) -> QueryResult:
        return self.query_service.execute_sql_result(
            query=value.sql,
            context={"lineage.tracing.enable": True, "scenario": DATA_ANALYSIS_INSTRUCTION},
            user_id=user_id,
        )

    def data2chart(self, *, value: Data2ChartInput) -> Data2ChartOutput:
        chart_type, series = _visualization_selection(value.query_result.data)
        return Data2ChartOutput(
            summaries=[],
            type=chart_type,
            series=series,
            query_result=value.query_result,
        )

    def data2summary(self, *, value: Data2SummaryInput) -> Data2SummaryOutput:
        summary = self._summarize(question=value.question, sql=value.sql, data=value.query_result.data)
        return Data2SummaryOutput(summaries=[summary] if summary else [])

    def create_natural_language_flow(self, *, question: str, user_id: str) -> FlowGraph:
        return DataAnalysisFlowFactory(service=self).analysis_from_natural_language(question=question, user_id=user_id)

    def create_sql_flow(self, *, sql: str, question: str | None = None, user_id: str) -> FlowGraph:
        return DataAnalysisFlowFactory(service=self).analysis_from_sql(sql=sql, question=question, user_id=user_id)

    def subflow_specs(self) -> list[SubflowSpec]:
        return DataAnalysisFlowFactory(service=self).subflow_specs()

    def _build_answer(
        self,
        *,
        question: str,
        sql: str,
        data: DatasetResult,
        chart: Data2ChartOutput,
        summary: Data2SummaryOutput,
    ) -> DataAnalysisAnswer:
        return DataAnalysisAnswer(
            summary="\n".join(summary.summaries),
            query_spec=QuerySpec(intent=question, sql=sql),
            data=data,
            components=_visualization_components(chart),
            warnings=list(data.warnings),
        )

    def _audit_analysis_completed(self, *, answer: DataAnalysisAnswer, user_id: str) -> None:
        self._audit(
            AuditEvent(
                operation="data_analysis.query",
                detail=f"completed rows={len(answer.data.rows)}",
                user_id=user_id,
                target_obj=DATA_ANALYSIS_INSTRUCTION,
            )
        )

    def _audit(self, event: AuditEvent) -> None:
        if self.audit_publisher is None:
            return
        try:
            self.audit_publisher.submit(event)
        except Exception:
            return

    def _generate_nl2sql_output(self, *, question: str, entities: list[dict[str, Any]], retrieved: list[dict[str, Any]]) -> Nl2SqlOutput:
        response = self.ai_gateway.chat_completion(
            self.completion_config_builder(),
            [
                {
                    "role": "system",
                    "content": (
                        "把用户问题转换为 JSON，只返回 sql 和 intent_function。"
                        "intent_function 必须是完整、单一的 Python 函数定义源码。"
                    ),
                },
                {"role": "user", "content": json.dumps({"question": question, "entities": entities[:20], "retrieved": retrieved[:5]}, ensure_ascii=False)},
            ],
            temperature=0.0,
            max_tokens=900,
        )
        payload = _json_object(response.get("content"))
        sql = str(payload.get("sql") or "").strip()
        if not sql:
            raise ValidationError(
                "模型没有生成可执行查询",
                error_code=ErrorCode.DATA_ANALYSIS_QUERY_GENERATION_FAILED,
            )
        intent_function = str(payload.get("intent_function") or "").strip()
        _validate_intent_function(intent_function)
        return Nl2SqlOutput(sql=sql, intent_function=intent_function)

    def _summarize(self, *, question: str, sql: str, data: DatasetResult) -> str:
        response = self.ai_gateway.chat_completion(
            self.completion_config_builder(),
            [
                {"role": "system", "content": "根据查询结果给出简洁中文结论。"},
                {"role": "user", "content": json.dumps({"question": question, "sql": sql, "rows": data.rows[:20]}, ensure_ascii=False)},
            ],
            temperature=0.1,
            max_tokens=400,
        )
        return str(response.get("content") or "").strip()


class DataAnalysisFlowFactory:
    """Builds composable AgentFlow graphs for data-analysis capabilities."""

    def __init__(self, *, service: DataAnalysisService) -> None:
        self.service = service

    def analysis_from_natural_language(self, *, question: str, user_id: str) -> FlowGraph:
        graph = self._analysis_graph(start_node=NL2SQL_NODE)
        self._add_nl2sql(graph=graph, question=question, user_id=user_id)
        self._add_sql2data(graph=graph, user_id=user_id)
        self._add_chart_summary_finalize(graph=graph, question=question, user_id=user_id)
        graph.add_edge(FlowEdge(source=NL2SQL_NODE, target=SQL2DATA_NODE))
        graph.add_edge(FlowEdge(source=SQL2DATA_NODE, target=DATA2CHART_NODE))
        graph.add_edge(FlowEdge(source=SQL2DATA_NODE, target=DATA2SUMMARY_NODE))
        graph.add_edge(FlowEdge(source=DATA2CHART_NODE, target=FINALIZE_NODE))
        graph.add_edge(FlowEdge(source=DATA2SUMMARY_NODE, target=FINALIZE_NODE))
        return graph

    def analysis_from_sql(self, *, sql: str, question: str | None, user_id: str) -> FlowGraph:
        graph = self._analysis_graph(start_node=SQL2DATA_NODE)
        graph.add_node(
            FlowNode(
                id=SQL2DATA_NODE,
                title="执行 SQL 查询",
                handler=self._sql2data_handler(user_id=user_id, initial_sql=sql, initial_question=question),
            )
        )
        self._add_chart_summary_finalize(graph=graph, question=question or "SQL 数据分析", user_id=user_id)
        graph.add_edge(FlowEdge(source=SQL2DATA_NODE, target=DATA2CHART_NODE))
        graph.add_edge(FlowEdge(source=SQL2DATA_NODE, target=DATA2SUMMARY_NODE))
        graph.add_edge(FlowEdge(source=DATA2CHART_NODE, target=FINALIZE_NODE))
        graph.add_edge(FlowEdge(source=DATA2SUMMARY_NODE, target=FINALIZE_NODE))
        return graph

    def nl2data(self, *, question: str, user_id: str) -> FlowGraph:
        graph = FlowGraph(start=NL2SQL_NODE)
        self._add_nl2sql(graph=graph, question=question, user_id=user_id)
        self._add_sql2data(graph=graph, user_id=user_id)
        graph.add_node(
            FlowNode(
                id=FINALIZE_NODE,
                title="完成数据查询",
                handler=lambda context: context.emit_answer(
                    {
                        "answerType": "DATA_ANALYSIS_STEP",
                        "answer": nl2data_output_to_dict(
                            Nl2DataOutput(
                                sql=context.get_state("nl2sql_output").sql,
                                intent_function=context.get_state("nl2sql_output").intent_function,
                                query_result=context.get_state("query_result"),
                            )
                        ),
                    }
                ),
            )
        )
        graph.add_edge(FlowEdge(source=NL2SQL_NODE, target=SQL2DATA_NODE))
        graph.add_edge(FlowEdge(source=SQL2DATA_NODE, target=FINALIZE_NODE))
        return graph

    def subflow_specs(self) -> list[SubflowSpec]:
        return [
            SubflowSpec(name="data_analysis.nl2sql", build_graph=lambda args: self._nl2sql_subflow(args)),
            SubflowSpec(name="data_analysis.sql2data", build_graph=lambda args: self._sql2data_subflow(args)),
            SubflowSpec(name="data_analysis.nl2data", build_graph=lambda args: self.nl2data(question=str(args.get("question") or ""), user_id=str(args.get("userId") or args.get("user_id") or ""))),
            SubflowSpec(name="data_analysis.data2chart", build_graph=lambda args: self._data2chart_subflow(args)),
            SubflowSpec(name="data_analysis.data2summary", build_graph=lambda args: self._data2summary_subflow(args)),
            SubflowSpec(name="data_analysis.analysis_from_nl", build_graph=lambda args: self.analysis_from_natural_language(question=str(args.get("question") or ""), user_id=str(args.get("userId") or args.get("user_id") or "")), event_policy=SubflowEventPolicy()),
            SubflowSpec(name="data_analysis.analysis_from_sql", build_graph=lambda args: self.analysis_from_sql(sql=str(args.get("sql") or ""), question=args.get("question"), user_id=str(args.get("userId") or args.get("user_id") or "")), event_policy=SubflowEventPolicy()),
        ]

    def _analysis_graph(self, *, start_node: str) -> FlowGraph:
        return FlowGraph(start=start_node)

    def _add_nl2sql(self, *, graph: FlowGraph, question: str, user_id: str) -> None:
        graph.add_node(
            FlowNode(
                id=NL2SQL_NODE,
                title="理解问题并生成查询",
                handler=self._nl2sql_handler(question=question, user_id=user_id),
            )
        )

    def _add_sql2data(self, *, graph: FlowGraph, user_id: str) -> None:
        graph.add_node(
            FlowNode(
                id=SQL2DATA_NODE,
                title="执行查询获取数据",
                handler=self._sql2data_handler(user_id=user_id),
            )
        )

    def _add_chart_summary_finalize(self, *, graph: FlowGraph, question: str, user_id: str) -> None:
        graph.add_node(
            FlowNode(
                id=DATA2CHART_NODE,
                title="生成可视化组件",
                handler=self._data2chart_handler(),
            )
        )
        graph.add_node(
            FlowNode(
                id=DATA2SUMMARY_NODE,
                title="生成分析结论",
                handler=self._data2summary_handler(question=question),
            )
        )
        graph.add_node(
            FlowNode(
                id=FINALIZE_NODE,
                title="完成智能问数",
                handler=self._finalize_handler(question=question, user_id=user_id),
            )
        )

    def _nl2sql_handler(self, *, question: str, user_id: str):
        def handler(context: FlowContext) -> None:
            output = self.service.nl2sql(value=Nl2SqlInput(question=question), user_id=user_id)
            context.set_state("question", question)
            context.set_state("nl2sql_output", output)

        return handler

    def _sql2data_handler(self, *, user_id: str, initial_sql: str | None = None, initial_question: str | None = None):
        def handler(context: FlowContext) -> None:
            generated = context.get_state("nl2sql_output")
            sql = str(generated.sql if generated is not None else initial_sql or "").strip()
            question = str(context.get_state("question") or initial_question or "SQL 数据分析")
            if not sql:
                raise ValidationError(
                    "SQL must not be empty",
                    error_code=ErrorCode.DATA_ANALYSIS_QUERY_GENERATION_FAILED,
                )
            context.set_state("question", question)
            context.set_state("sql", sql)
            context.set_state("query_result", self.service.sql2data(value=Sql2DataInput(question=question, sql=sql), user_id=user_id))

        return handler

    def _data2chart_handler(self):
        def handler(context: FlowContext) -> None:
            value = Data2ChartInput(
                question=str(context.get_state("question") or ""),
                query_result=context.get_state("query_result"),
            )
            context.set_state("chart_output", self.service.data2chart(value=value))

        return handler

    def _data2summary_handler(self, *, question: str):
        def handler(context: FlowContext) -> None:
            current_question = str(context.get_state("question") or question)
            value = Data2SummaryInput(
                question=current_question,
                sql=str(context.get_state("sql") or context.get_state("nl2sql_output").sql),
                query_result=context.get_state("query_result"),
            )
            context.set_state("summary_output", self.service.data2summary(value=value))

        return handler

    def _finalize_handler(self, *, question: str, user_id: str):
        def handler(context: FlowContext) -> None:
            current_question = str(context.get_state("question") or question)
            query_result = context.get_state("query_result")
            answer = self.service._build_answer(
                question=current_question,
                sql=str(context.get_state("sql") or context.get_state("nl2sql_output").sql),
                data=query_result.data,
                chart=context.get_state("chart_output"),
                summary=context.get_state("summary_output"),
            )
            self.service._audit_analysis_completed(answer=answer, user_id=user_id)
            context.emit_answer({"answerType": "DATA_ANALYSIS", "answer": data_analysis_answer_to_dict(answer)})

        return handler

    def _nl2sql_subflow(self, args: dict[str, Any]) -> FlowGraph:
        question = nl2sql_input_from_dict(args).question
        user_id = str(args.get("userId") or args.get("user_id") or "")
        graph = FlowGraph(start=NL2SQL_NODE)
        self._add_nl2sql(graph=graph, question=question, user_id=user_id)
        graph.add_node(
            FlowNode(
                id=FINALIZE_NODE,
                title="输出查询语句",
                handler=lambda context: context.emit_answer(
                    {"answerType": "DATA_ANALYSIS_STEP", "answer": nl2sql_output_to_dict(context.get_state("nl2sql_output"))}
                ),
            )
        )
        graph.add_edge(FlowEdge(source=NL2SQL_NODE, target=FINALIZE_NODE))
        return graph

    def _sql2data_subflow(self, args: dict[str, Any]) -> FlowGraph:
        value = sql2data_input_from_dict(args)
        graph = FlowGraph(start=SQL2DATA_NODE)
        graph.add_node(
            FlowNode(
                id=SQL2DATA_NODE,
                title="执行查询获取数据",
                handler=self._sql2data_handler(
                    user_id=str(args.get("userId") or args.get("user_id") or ""),
                    initial_sql=value.sql,
                    initial_question=value.question,
                ),
            )
        )
        graph.add_node(
            FlowNode(
                id=FINALIZE_NODE,
                title="输出数据集",
                handler=lambda context: context.emit_answer(
                    {"answerType": "DATA_ANALYSIS_STEP", "answer": query_result_to_dict(context.get_state("query_result"))}
                ),
            )
        )
        graph.add_edge(FlowEdge(source=SQL2DATA_NODE, target=FINALIZE_NODE))
        return graph

    def _data2chart_subflow(self, args: dict[str, Any]) -> FlowGraph:
        graph = FlowGraph(start=DATA2CHART_NODE)

        def handler(context: FlowContext) -> None:
            value = data2chart_input_from_dict(args)
            context.emit_answer({"answerType": "DATA_ANALYSIS_STEP", "answer": data2chart_output_to_dict(self.service.data2chart(value=value))})

        graph.add_node(FlowNode(id=DATA2CHART_NODE, title="生成可视化组件", handler=handler))
        return graph

    def _data2summary_subflow(self, args: dict[str, Any]) -> FlowGraph:
        graph = FlowGraph(start=DATA2SUMMARY_NODE)

        def handler(context: FlowContext) -> None:
            value = data2summary_input_from_dict(args)
            context.emit_answer({"answerType": "DATA_ANALYSIS_STEP", "answer": data2summary_output_to_dict(self.service.data2summary(value=value))})

        graph.add_node(FlowNode(id=DATA2SUMMARY_NODE, title="生成分析结论", handler=handler))
        return graph


def _json_object(raw: object) -> dict[str, Any]:
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.removeprefix("json").strip()
    try:
        payload = json.loads(text)
    except ValueError as exc:
        raise ValidationError(
            "模型没有返回合法 nl2sql JSON",
            error_code=ErrorCode.DATA_ANALYSIS_QUERY_GENERATION_FAILED,
        ) from exc
    if not isinstance(payload, dict):
        raise ValidationError(
            "模型 nl2sql 输出必须是 JSON object",
            error_code=ErrorCode.DATA_ANALYSIS_QUERY_GENERATION_FAILED,
        )
    return payload


def _validate_intent_function(source: str) -> None:
    if not source:
        raise ValidationError(
            "模型没有生成 intent_function",
            error_code=ErrorCode.DATA_ANALYSIS_QUERY_GENERATION_FAILED,
        )
    try:
        module = ast.parse(source)
    except SyntaxError as exc:
        raise ValidationError(
            "模型生成的 intent_function 不是合法 Python 函数定义",
            error_code=ErrorCode.DATA_ANALYSIS_QUERY_GENERATION_FAILED,
        ) from exc
    if len(module.body) != 1 or not isinstance(module.body[0], (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise ValidationError(
            "模型生成的 intent_function 必须是单个完整函数定义",
            error_code=ErrorCode.DATA_ANALYSIS_QUERY_GENERATION_FAILED,
        )


def _visualization_selection(data: DatasetResult) -> tuple[str, list[dict[str, Any]]]:
    columns = [item.key for item in data.columns]
    numeric = next((item.key for item in data.columns if str(item.metadata.get("type") or "").lower() in {"int", "integer", "long", "float", "double", "number"}), None)
    dimension = next((item for item in columns if item != numeric), None)
    if not numeric or not dimension:
        return "table", []
    return "bar", [{"type": "bar", "name": numeric, "dataKey": numeric}]


def _visualization_components(output: Data2ChartOutput) -> list[dict[str, Any]]:
    data = output.query_result.data
    columns = [item.key for item in data.columns]
    table = {
        "id": "analysis_table",
        "type": "table",
        "title": "查询结果",
        "dataProperties": {"columns": [{"key": item.key, **item.metadata} for item in data.columns], "data": list(data.rows)},
    }
    if output.type == "table" or not output.series:
        return [table]
    numeric = str(output.series[0].get("dataKey") or "")
    dimension = next((item for item in columns if item != numeric), None)
    if not numeric or not dimension:
        return [table]
    chart_component = {
        "id": "analysis_chart",
        "type": "chart",
        "title": "查询结果图表",
        "dataProperties": {
            "chartType": output.type,
            "columns": [{"key": item.key, **item.metadata} for item in data.columns],
            "data": list(data.rows),
            "series": list(output.series),
            "xAxis": {"field": dimension},
            "yAxis": {"field": numeric},
        },
    }
    return [chart_component, table]
