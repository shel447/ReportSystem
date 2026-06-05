"""Application orchestration for reusable data analysis and query execution."""

from __future__ import annotations

import json
from typing import Any

from ....shared.agentflow import FlowContext, FlowEdge, FlowGraph, FlowNode, SubflowEventPolicy, SubflowSpec
from ....shared.kernel.errors import ErrorCode, ValidationError
from ....shared.kernel.audit import AuditEvent
from ....shared.kernel.safety import GuardrailGateway
from ..domain.models import DataAnalysisAnswer, DatasetColumn, DatasetResult, QuerySpec, data_analysis_answer_to_dict, dataset_result_to_dict, query_spec_to_dict
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
        audit_dispatcher=None,
    ) -> None:
        self.query_service = query_service
        self.data_catalog_gateway = data_catalog_gateway
        self.knowledge_gateway = knowledge_gateway
        self.guardrail_gateway = guardrail_gateway
        self.ai_gateway = ai_gateway
        self.completion_config_builder = completion_config_builder
        self.audit_dispatcher = audit_dispatcher

    def analyze_from_natural_language(self, *, question: str, user_id: str) -> DataAnalysisAnswer:
        spec, data = self.nl2data(question=question, user_id=user_id)
        components = self.data2chart(data=data)
        answer = self._build_answer(
            question=question,
            spec=spec,
            data=data,
            components=components,
            summary=self.data2summary(question=question, spec=spec, data=data),
        )
        self._audit_analysis_completed(answer=answer, user_id=user_id)
        return answer

    def analyze_from_sql(self, *, sql: str, question: str | None = None, user_id: str) -> DataAnalysisAnswer:
        spec = QuerySpec(intent=str(question or "SQL 数据分析"), sql=str(sql or "").strip())
        if not spec.sql:
            raise ValidationError(
                "SQL must not be empty",
                error_code=ErrorCode.DATA_ANALYSIS_QUERY_GENERATION_FAILED,
            )
        data = self.sql2data(spec=spec, user_id=user_id)
        components = self.data2chart(data=data)
        answer = self._build_answer(
            question=question or spec.intent,
            spec=spec,
            data=data,
            components=components,
            summary=self.data2summary(question=question or spec.intent, spec=spec, data=data),
        )
        self._audit_analysis_completed(answer=answer, user_id=user_id)
        return answer

    def nl2data(self, *, question: str, user_id: str) -> tuple[QuerySpec, DatasetResult]:
        spec = self.nl2sql(question=question, user_id=user_id)
        return spec, self.sql2data(spec=spec, user_id=user_id)

    def nl2sql(self, *, question: str, user_id: str) -> QuerySpec:
        entities = self.data_catalog_gateway.list_logical_entities(user_id=user_id)
        try:
            retrieved = self.knowledge_gateway.retrieve_multi_index(query=question, user_id=user_id)
        except Exception:
            retrieved = []
        spec = self._generate_query_spec(question=question, entities=entities, retrieved=retrieved)
        security = self.guardrail_gateway.check_application_security(kind="nl2sql", content=spec.sql, user_id=user_id)
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
        return spec

    def sql2data(self, *, spec: QuerySpec, user_id: str) -> DatasetResult:
        data = self.query_service.execute_sql(
            query=spec.sql,
            context={"lineage.tracing.enable": True, "scenario": DATA_ANALYSIS_INSTRUCTION},
            user_id=user_id,
        )
        return data

    def data2chart(self, *, data: DatasetResult) -> list[dict[str, Any]]:
        return _visualization_components(data)

    def data2summary(self, *, question: str, spec: QuerySpec, data: DatasetResult) -> str:
        return self._summarize(question=question, spec=spec, data=data)

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
        spec: QuerySpec,
        data: DatasetResult,
        components: list[dict[str, Any]],
        summary: str,
    ) -> DataAnalysisAnswer:
        return DataAnalysisAnswer(
            summary=summary,
            query_spec=spec,
            data=data,
            components=components,
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
        if self.audit_dispatcher is None:
            return
        try:
            self.audit_dispatcher.submit(event)
        except Exception:
            return

    def _generate_query_spec(self, *, question: str, entities: list[dict[str, Any]], retrieved: list[dict[str, Any]]) -> QuerySpec:
        response = self.ai_gateway.chat_completion(
            self.completion_config_builder(),
            [
                {"role": "system", "content": "把用户问题转换为 JSON，必须包含 sql，可选 intent/entities/dimensions/measures/filters。只返回 JSON。"},
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
        return QuerySpec(
            intent=str(payload.get("intent") or question),
            sql=sql,
            entities=[str(item) for item in list(payload.get("entities") or [])],
            dimensions=[str(item) for item in list(payload.get("dimensions") or [])],
            measures=[str(item) for item in list(payload.get("measures") or [])],
            filters=[dict(item) for item in list(payload.get("filters") or []) if isinstance(item, dict)],
        )

    def _summarize(self, *, question: str, spec: QuerySpec, data: DatasetResult) -> str:
        response = self.ai_gateway.chat_completion(
            self.completion_config_builder(),
            [
                {"role": "system", "content": "根据查询结果给出简洁中文结论。"},
                {"role": "user", "content": json.dumps({"question": question, "sql": spec.sql, "rows": data.rows[:20]}, ensure_ascii=False)},
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
                        "answer": {
                            "querySpec": query_spec_to_dict(context.get_state("query_spec")),
                            "data": dataset_result_to_dict(context.get_state("data")),
                        },
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
            spec = self.service.nl2sql(question=question, user_id=user_id)
            context.set_state("question", question)
            context.set_state("query_spec", spec)

        return handler

    def _sql2data_handler(self, *, user_id: str, initial_sql: str | None = None, initial_question: str | None = None):
        def handler(context: FlowContext) -> None:
            spec = context.get_state("query_spec")
            if spec is None:
                sql = str(initial_sql or "").strip()
                if not sql:
                    raise ValidationError(
                        "SQL must not be empty",
                        error_code=ErrorCode.DATA_ANALYSIS_QUERY_GENERATION_FAILED,
                    )
                spec = QuerySpec(intent=str(initial_question or "SQL 数据分析"), sql=sql)
                context.set_state("query_spec", spec)
                context.set_state("question", initial_question or spec.intent)
            data = self.service.sql2data(spec=spec, user_id=user_id)
            context.set_state("data", data)

        return handler

    def _data2chart_handler(self):
        def handler(context: FlowContext) -> None:
            data = context.get_state("data")
            context.set_state("components", self.service.data2chart(data=data))

        return handler

    def _data2summary_handler(self, *, question: str):
        def handler(context: FlowContext) -> None:
            spec = context.get_state("query_spec")
            data = context.get_state("data")
            current_question = str(context.get_state("question") or question)
            context.set_state("summary", self.service.data2summary(question=current_question, spec=spec, data=data))

        return handler

    def _finalize_handler(self, *, question: str, user_id: str):
        def handler(context: FlowContext) -> None:
            spec = context.get_state("query_spec")
            data = context.get_state("data")
            components = context.get_state("components", [])
            summary = str(context.get_state("summary") or "")
            current_question = str(context.get_state("question") or question)
            answer = self.service._build_answer(question=current_question, spec=spec, data=data, components=list(components), summary=summary)
            self.service._audit_analysis_completed(answer=answer, user_id=user_id)
            context.emit_answer({"answerType": "DATA_ANALYSIS", "answer": data_analysis_answer_to_dict(answer)})

        return handler

    def _nl2sql_subflow(self, args: dict[str, Any]) -> FlowGraph:
        question = str(args.get("question") or "")
        user_id = str(args.get("userId") or args.get("user_id") or "")
        graph = FlowGraph(start=NL2SQL_NODE)
        self._add_nl2sql(graph=graph, question=question, user_id=user_id)
        graph.add_node(
            FlowNode(
                id=FINALIZE_NODE,
                title="输出查询语句",
                handler=lambda context: context.emit_answer(
                    {"answerType": "DATA_ANALYSIS_STEP", "answer": {"querySpec": query_spec_to_dict(context.get_state("query_spec"))}}
                ),
            )
        )
        graph.add_edge(FlowEdge(source=NL2SQL_NODE, target=FINALIZE_NODE))
        return graph

    def _sql2data_subflow(self, args: dict[str, Any]) -> FlowGraph:
        graph = FlowGraph(start=SQL2DATA_NODE)
        graph.add_node(
            FlowNode(
                id=SQL2DATA_NODE,
                title="执行查询获取数据",
                handler=self._sql2data_handler(
                    user_id=str(args.get("userId") or args.get("user_id") or ""),
                    initial_sql=str(args.get("sql") or ""),
                    initial_question=args.get("question"),
                ),
            )
        )
        graph.add_node(
            FlowNode(
                id=FINALIZE_NODE,
                title="输出数据集",
                handler=lambda context: context.emit_answer(
                    {"answerType": "DATA_ANALYSIS_STEP", "answer": {"data": dataset_result_to_dict(context.get_state("data"))}}
                ),
            )
        )
        graph.add_edge(FlowEdge(source=SQL2DATA_NODE, target=FINALIZE_NODE))
        return graph

    def _data2chart_subflow(self, args: dict[str, Any]) -> FlowGraph:
        graph = FlowGraph(start=DATA2CHART_NODE)

        def handler(context: FlowContext) -> None:
            data = _dataset_from_payload(args.get("data") or {})
            components = self.service.data2chart(data=data)
            context.emit_answer({"answerType": "DATA_ANALYSIS_STEP", "answer": {"components": components}})

        graph.add_node(FlowNode(id=DATA2CHART_NODE, title="生成可视化组件", handler=handler))
        return graph

    def _data2summary_subflow(self, args: dict[str, Any]) -> FlowGraph:
        graph = FlowGraph(start=DATA2SUMMARY_NODE)

        def handler(context: FlowContext) -> None:
            data = _dataset_from_payload(args.get("data") or {})
            spec = _query_spec_from_payload(args.get("querySpec") or {"sql": args.get("sql") or "", "intent": args.get("question") or "数据分析"})
            summary = self.service.data2summary(question=str(args.get("question") or spec.intent), spec=spec, data=data)
            context.emit_answer({"answerType": "DATA_ANALYSIS_STEP", "answer": {"summary": summary}})

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
            "模型没有返回合法 QuerySpec JSON",
            error_code=ErrorCode.DATA_ANALYSIS_QUERY_GENERATION_FAILED,
        ) from exc
    if not isinstance(payload, dict):
        raise ValidationError(
            "模型 QuerySpec 必须是 JSON object",
            error_code=ErrorCode.DATA_ANALYSIS_QUERY_GENERATION_FAILED,
        )
    return payload


def _query_spec_from_payload(payload: object) -> QuerySpec:
    data = payload if isinstance(payload, dict) else {}
    sql = str(data.get("sql") or "").strip()
    if not sql:
        raise ValidationError(
            "QuerySpec.sql is required",
            error_code=ErrorCode.DATA_ANALYSIS_QUERY_GENERATION_FAILED,
        )
    return QuerySpec(
        intent=str(data.get("intent") or "数据分析"),
        sql=sql,
        entities=[str(item) for item in list(data.get("entities") or [])],
        dimensions=[str(item) for item in list(data.get("dimensions") or [])],
        measures=[str(item) for item in list(data.get("measures") or [])],
        filters=[dict(item) for item in list(data.get("filters") or []) if isinstance(item, dict)],
    )


def _dataset_from_payload(payload: object) -> DatasetResult:
    data = payload if isinstance(payload, dict) else {}
    raw_columns = data.get("columns") or {}
    columns: list[DatasetColumn] = []
    if isinstance(raw_columns, dict):
        columns = [DatasetColumn(key=str(key), metadata=dict(value if isinstance(value, dict) else {})) for key, value in raw_columns.items()]
    elif isinstance(raw_columns, list):
        for item in raw_columns:
            if isinstance(item, dict):
                key = str(item.get("key") or item.get("field") or "")
                if key:
                    columns.append(DatasetColumn(key=key, metadata={k: v for k, v in item.items() if k not in {"key", "field"}}))
    rows = [dict(item) for item in list(data.get("results") or data.get("rows") or []) if isinstance(item, dict)]
    warnings = [dict(item) for item in list(data.get("warnings") or []) if isinstance(item, dict)]
    return DatasetResult(columns=columns, rows=rows, warnings=warnings)


def _visualization_components(data: DatasetResult) -> list[dict[str, Any]]:
    columns = [item.key for item in data.columns]
    table = {
        "id": "analysis_table",
        "type": "table",
        "title": "查询结果",
        "dataProperties": {"columns": [{"key": item.key, **item.metadata} for item in data.columns], "data": list(data.rows)},
    }
    numeric = next((item.key for item in data.columns if str(item.metadata.get("type") or "").lower() in {"int", "integer", "long", "float", "double", "number"}), None)
    dimension = next((item for item in columns if item != numeric), None)
    if not numeric or not dimension:
        return [table]
    chart = {
        "id": "analysis_chart",
        "type": "chart",
        "title": "查询结果图表",
        "dataProperties": {
            "chartType": "bar",
            "columns": [{"key": item.key, **item.metadata} for item in data.columns],
            "data": list(data.rows),
            "series": [{"type": "bar", "name": numeric, "dataKey": numeric}],
            "xAxis": {"field": dimension},
            "yAxis": {"field": numeric},
        },
    }
    return [chart, table]
