"""Application orchestration for reusable data analysis and query execution."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

import yaml

from ....shared.agentflow import FlowContext, FlowEdge, FlowGraph, FlowNode, SubflowEventPolicy, SubflowSpec
from ....shared.agentflow.metrics import record_unique_metric
from ....shared.kernel.errors import ApplicationError, ErrorCode, ValidationError
from ....shared.kernel.audit import AuditEvent, AuditPublisher
from ....shared.kernel.safety import GuardrailGateway
from ....shared.prompts import PromptCatalog
from ..domain.models import (
    Data2ChartInput,
    Data2ChartOutput,
    Data2SummaryInput,
    Data2SummaryOutput,
    DataAnalysisAnswer,
    DatasetResult,
    Nl2DataOutput,
    Nl2SqlCompileError,
    Nl2SqlContext,
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
from .ports import (
    ApiDatasetGateway,
    DataCatalogGateway,
    KnowledgeGateway,
    LogicalEntityValidator,
    Nl2SqlCompiler,
    OneQueryGateway,
)


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
        prompt_catalog: PromptCatalog,
        nl2sql_compiler: Nl2SqlCompiler,
        logical_entity_validator: LogicalEntityValidator,
        audit_publisher: AuditPublisher | None = None,
    ) -> None:
        self.query_service = query_service
        self.data_catalog_gateway = data_catalog_gateway
        self.knowledge_gateway = knowledge_gateway
        self.guardrail_gateway = guardrail_gateway
        self.ai_gateway = ai_gateway
        self.completion_config_builder = completion_config_builder
        self.prompt_catalog = prompt_catalog
        self.nl2sql_compiler = nl2sql_compiler
        self.logical_entity_validator = logical_entity_validator
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
        return Nl2DataOutput(sql=generated.sql, query_result=query_result)

    def nl2sql(self, *, value: Nl2SqlInput, user_id: str) -> Nl2SqlOutput:
        context = self._build_nl2sql_context(question=value.question, user_id=user_id)
        output = self._generate_nl2sql_output(context=context)
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

    def _build_nl2sql_context(self, *, question: str, user_id: str) -> Nl2SqlContext:
        listed = self.data_catalog_gateway.list_logical_entities(user_id=user_id)
        selected = _select_entities(question=question, entities=listed)
        details: list[dict[str, Any]] = []
        for item in selected:
            name = _entity_name(item)
            if not name:
                continue
            detail = dict(self.data_catalog_gateway.get_logical_entity(name=name, user_id=user_id))
            validated = self.logical_entity_validator.validate(entity=detail, expected_name=name)
            details.append(validated)
            record_unique_metric("datacatalog.logical_entity.used", name)
        try:
            relations = self.data_catalog_gateway.list_logical_relations(user_id=user_id)
        except Exception:
            relations = []
        try:
            few_shots = self.knowledge_gateway.retrieve_sql_few_shot(query=question, user_id=user_id)
        except Exception:
            few_shots = []
        return Nl2SqlContext(
            question=question,
            entities=tuple(details),
            relations=tuple(_select_relations(relations=relations, entities=details)),
            few_shots=tuple(few_shots[:5]),
        )

    def sql2data(self, *, value: Sql2DataInput, user_id: str) -> QueryResult:
        return self.query_service.execute_sql_result(
            query=value.sql,
            context={"lineage.tracing.enable": True, "scenario": DATA_ANALYSIS_INSTRUCTION},
            user_id=user_id,
        )

    def data2chart(self, *, value: Data2ChartInput) -> Data2ChartOutput:
        data = value.query_result.data
        response = self._complete(
            prompt=[{
                "role": "system",
                "content": self.prompt_catalog.render(
                    "figure.any",
                    user_question=value.question,
                    query_results=json.dumps(data.rows[:50], ensure_ascii=False),
                    field_descriptions=json.dumps(
                        [{"column": item.key, **item.metadata} for item in data.columns],
                        ensure_ascii=False,
                    ),
                ),
            }],
            error_code=ErrorCode.DATA_ANALYSIS_VISUALIZATION_FAILED,
            error_message="智能问数可视化模型调用失败。",
            temperature=0.0,
            max_tokens=1000,
        )
        return _parse_chart_output(response.get("content"), query_result=value.query_result)

    def data2summary(self, *, value: Data2SummaryInput) -> Data2SummaryOutput:
        data = value.query_result.data
        response = self._complete(
            prompt=[{
                "role": "system",
                "content": self.prompt_catalog.render(
                    "figure.summary_system",
                    query=value.question,
                    sql=value.sql,
                    result_fields=json.dumps(
                        [{"column": item.key, **item.metadata} for item in data.columns],
                        ensure_ascii=False,
                    ),
                    data_sample=json.dumps(data.rows[:20], ensure_ascii=False),
                ),
            }],
            error_code=ErrorCode.DATA_ANALYSIS_SUMMARY_FAILED,
            error_message="智能问数总结模型调用失败。",
            temperature=0.1,
            max_tokens=700,
        )
        return _parse_summary_output(response.get("content"))

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
            title=summary.title or chart.title,
            sql_explanation=summary.sql_explanation,
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

    def _generate_nl2sql_output(self, *, context: Nl2SqlContext) -> Nl2SqlOutput:
        last_error: Nl2SqlCompileError | None = None
        for attempt in range(1, 4):
            response = self._complete(
                prompt=self._nl2sql_prompt(context=context, attempt=attempt, last_error=last_error),
                error_code=ErrorCode.DATA_ANALYSIS_QUERY_GENERATION_FAILED,
                error_message="智能问数查询生成模型调用失败。",
                temperature=0.0,
                max_tokens=2400,
            )
            try:
                source = _generated_ibis_source(response.get("content"))
                return Nl2SqlOutput(sql=self.nl2sql_compiler.compile(source=source, context=context))
            except Nl2SqlCompileError as exc:
                last_error = exc
        raise ValidationError(
            "模型生成的 Ibis 查询在三次尝试后仍无法编译。",
            details={"stage": last_error.stage if last_error else "generation", "attempts": 3},
            error_code=ErrorCode.DATA_ANALYSIS_QUERY_GENERATION_FAILED,
        )

    def _nl2sql_prompt(
        self,
        *,
        context: Nl2SqlContext,
        attempt: int,
        last_error: Nl2SqlCompileError | None,
    ) -> list[dict[str, Any]]:
        error_feedback = ""
        if last_error is not None:
            error_feedback = f"\nPrevious attempt failed at {last_error.stage}: {last_error}\nPlease repair the function."
        knowledge = self.prompt_catalog.render(
            "data_analysis.knowledge_template",
            knowledge_doc=json.dumps(context.few_shots, ensure_ascii=False),
        )
        relations = self.prompt_catalog.render(
            "data_analysis.table_relation_graph",
            foreign_key_lis=json.dumps(context.relations, ensure_ascii=False),
        )
        similar_queries = self.prompt_catalog.render(
            "data_analysis.similar_query_template",
            topk_samples=json.dumps(context.few_shots, ensure_ascii=False),
        )
        ibis_code = self.prompt_catalog.render(
            "data_analysis.ibis_code_template",
            import_part="import ibis\nfrom ibis import _\nfrom typing import Any",
            utility_functions=(
                "def create_recursive_query(root_table_expr, id_col: str, parent_col: str, "
                "start_condition=None, max_depth: int = 2, include_columns=None, "
                "include_root_layer: bool = False): ...\n"
                "def create_device2kpi_wide_table(device_table, kpi_metrics_table, "
                "intermediate_tables): ...\n"
                "def get_tables_columns(table_exprs): ..."
            ),
            table_definitions=_ibis_table_definitions(context.entities),
            cast_unknown_type_columns_code="",
            intfunc_param_definitions="",
            context_functions="",
            run_historical_intent_functions="",
        )
        main = self.prompt_catalog.render(
            "data_analysis.main_template",
            knowledge=knowledge,
            table_relation_graph=relations,
            similar_queries=similar_queries,
            ibis_code=ibis_code,
            system_time=datetime.now(timezone.utc).isoformat(),
            current_dialogue=f"User: {context.question}{error_feedback}",
            THINKING_MODE="/no_think",
        )
        return [
            {"role": "system", "content": self.prompt_catalog.render("data_analysis.system_prompt")},
            {"role": "user", "content": f"Attempt {attempt}/3\n{main}"},
        ]

    def _complete(
        self,
        *,
        prompt: list[dict[str, Any]],
        error_code: str,
        error_message: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        try:
            return self.ai_gateway.chat_completion(
                self.completion_config_builder(),
                prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except ApplicationError as exc:
            raise ApplicationError(
                error_message,
                details=dict(exc.details),
                error_code=error_code,
                category="upstream",
                retryable=exc.retryable,
                source=exc.source,
                http_status=exc.http_status,
            ) from exc
        except Exception as exc:
            raise ApplicationError(
                error_message,
                error_code=error_code,
                category="upstream",
                retryable=False,
                http_status=502,
            ) from exc

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


def _generated_ibis_source(raw: object) -> str:
    payload = _json_object(raw)
    source = str(payload.get("implementation") or "").strip()
    if not source:
        raise Nl2SqlCompileError("generation", "Model response does not contain implementation")
    return source


def _entity_name(entity: dict[str, Any]) -> str:
    return str(entity.get("name") or entity.get("logicalEntityName") or entity.get("tableName") or "").strip()


def _select_entities(*, question: str, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    terms = {part.lower() for part in question.replace("，", " ").replace(",", " ").split() if part}
    ranked = sorted(
        entities,
        key=lambda item: sum(term in json.dumps(item, ensure_ascii=False).lower() for term in terms),
        reverse=True,
    )
    return ranked[:8]


def _select_relations(*, relations: list[dict[str, Any]], entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    names = {_entity_name(item) for item in entities}
    selected = [item for item in relations if any(name and name in json.dumps(item, ensure_ascii=False) for name in names)]
    return selected[:50]


def _ibis_table_definitions(entities: tuple[dict[str, Any], ...]) -> str:
    lines = ["class QueryConfig:"]
    for entity in entities:
        name = _entity_name(entity)
        if not name or not name.isidentifier():
            continue
        raw_fields = (entity.get("schema") or {}).get("fields") or []
        fields = {}
        complex_fields = []
        for item in raw_fields:
            field_name = str(item.get("name") or "").strip()
            field_type = str((item.get("type") or {}).get("type") or "").strip()
            if not field_name:
                continue
            if field_type in {"array", "record", "object"}:
                complex_fields.append(field_name)
                continue
            fields[field_name] = field_type
        lines.append(f"    # {json.dumps(entity, ensure_ascii=False)}")
        if complex_fields:
            lines.append(f"    # Complex fields are metadata-only and cannot be queried: {', '.join(complex_fields)}")
        lines.append(f"    {name} = ibis.table({json.dumps(fields, ensure_ascii=False)}, name={name!r})")
    if len(lines) == 1:
        lines.append("    pass")
    return "\n".join(lines)


def _yaml_object(raw: object, *, error_code: str, label: str) -> dict[str, Any]:
    text = _strip_code_fence(str(raw or "").strip())
    try:
        payload = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValidationError(f"{label}不是合法 YAML。", error_code=error_code) from exc
    if not isinstance(payload, dict):
        raise ValidationError(f"{label}必须是 YAML object。", error_code=error_code)
    return payload


def _parse_chart_output(raw: object, *, query_result: QueryResult) -> Data2ChartOutput:
    payload = _yaml_object(
        raw,
        error_code=ErrorCode.DATA_ANALYSIS_VISUALIZATION_FAILED,
        label="可视化模型输出",
    )
    type_map = {
        "text": "text", "table": "table", "bar": "bar", "line": "line",
        "multiline": "line", "pie": "pie", "ring": "pie", "scatter": "scatter",
        "radar": "radar", "gauge": "gauge", "candlestick": "candlestick",
    }
    series_payload = payload.get("series") or []
    if not isinstance(series_payload, list) or any(not isinstance(item, dict) for item in series_payload):
        raise ValidationError(
            "可视化 series 必须是对象数组。",
            error_code=ErrorCode.DATA_ANALYSIS_VISUALIZATION_FAILED,
        )
    raw_type = str(payload.get("type") or "").strip().lower()
    if raw_type == "chart":
        if not series_payload:
            raise ValidationError(
                "Chart 可视化必须在 series 中声明具体图表类型。",
                error_code=ErrorCode.DATA_ANALYSIS_VISUALIZATION_FAILED,
            )
        raw_visual_type = str(series_payload[0].get("type") or "").strip().lower()
    else:
        raw_visual_type = raw_type
    chart_type = type_map.get(raw_visual_type)
    if chart_type is None:
        raise ValidationError(
            f"不支持的可视化类型：{payload.get('type')}",
            error_code=ErrorCode.DATA_ANALYSIS_VISUALIZATION_FAILED,
        )
    columns = {item.key for item in query_result.data.columns}
    series: list[dict[str, Any]] = []
    field_names = {"ex", "ey", "ename", "evalue", "time", "open", "close", "lowest", "highest", "volume"}
    for item in series_payload:
        normalized = dict(item)
        item_type = str(item.get("type") or raw_visual_type).strip().lower()
        normalized_item_type = type_map.get(item_type)
        if normalized_item_type is None or normalized_item_type != chart_type:
            raise ValidationError(
                f"series 图表类型不一致或不受支持：{item.get('type')}",
                error_code=ErrorCode.DATA_ANALYSIS_VISUALIZATION_FAILED,
            )
        normalized["type"] = normalized_item_type
        if item_type == "ring":
            normalized["radius"] = ["45%", "70%"]
        for field_name in field_names:
            field = normalized.get(field_name)
            if field is not None and str(field) not in columns:
                raise ValidationError(
                    f"可视化引用了不存在的字段：{field}",
                    error_code=ErrorCode.DATA_ANALYSIS_VISUALIZATION_FAILED,
                )
        series.append(normalized)
    if chart_type not in {"table", "text"} and not series:
        raise ValidationError(
            "图表可视化必须包含 series。",
            error_code=ErrorCode.DATA_ANALYSIS_VISUALIZATION_FAILED,
        )
    summaries = payload.get("summaries") or []
    if not isinstance(summaries, list) or any(not isinstance(item, str) for item in summaries):
        raise ValidationError(
            "可视化 summaries 必须是字符串数组。",
            error_code=ErrorCode.DATA_ANALYSIS_VISUALIZATION_FAILED,
        )
    return Data2ChartOutput(
        summaries=list(summaries),
        type=chart_type,
        series=series,
        query_result=query_result,
        title=str(payload.get("title") or "").strip(),
        content=payload.get("content"),
    )


def _parse_summary_output(raw: object) -> Data2SummaryOutput:
    payload = _yaml_object(
        raw,
        error_code=ErrorCode.DATA_ANALYSIS_SUMMARY_FAILED,
        label="查询总结模型输出",
    )
    summaries = payload.get("summaries")
    if not isinstance(summaries, list) or any(not isinstance(item, str) or not item.strip() for item in summaries):
        raise ValidationError(
            "查询总结 summaries 必须是非空字符串数组。",
            error_code=ErrorCode.DATA_ANALYSIS_SUMMARY_FAILED,
        )
    title = payload.get("title")
    sql_explanation = payload.get("sql_explanation")
    if not isinstance(title, str) or not title.strip() or not isinstance(sql_explanation, str) or not sql_explanation.strip():
        raise ValidationError(
            "查询总结必须包含 title 和 sql_explanation。",
            error_code=ErrorCode.DATA_ANALYSIS_SUMMARY_FAILED,
        )
    return Data2SummaryOutput(
        summaries=[item.strip() for item in summaries],
        title=title.strip(),
        sql_explanation=sql_explanation.strip(),
    )


def _strip_code_fence(content: str) -> str:
    if not content.startswith("```"):
        return content
    lines = content.splitlines()
    lines = lines[1:] if lines and lines[0].startswith("```") else lines
    lines = lines[:-1] if lines and lines[-1].strip() == "```" else lines
    return "\n".join(lines).strip()


def _visualization_components(output: Data2ChartOutput) -> list[dict[str, Any]]:
    data = output.query_result.data
    columns = [item.key for item in data.columns]
    table = {
        "id": "analysis_table",
        "type": "table",
        "title": "查询结果",
        "dataProperties": {"columns": [{"key": item.key, **item.metadata} for item in data.columns], "data": list(data.rows)},
    }
    if output.type == "text":
        return [{
            "id": "analysis_text",
            "type": "text",
            "title": output.title,
            "dataProperties": {"content": str(output.content or "")},
        }, table]
    if output.type == "table" or not output.series:
        return [table]
    first = output.series[0]
    dimension = str(first.get("ex") or first.get("ename") or first.get("time") or "")
    numeric = str(first.get("ey") or first.get("evalue") or first.get("close") or "")
    if not numeric or not dimension or numeric not in columns or dimension not in columns:
        return [table]
    chart_component = {
        "id": "analysis_chart",
        "type": "chart",
        "title": output.title or "查询结果图表",
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
