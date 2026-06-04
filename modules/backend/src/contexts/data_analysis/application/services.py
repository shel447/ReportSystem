"""Application orchestration for reusable data analysis and query execution."""

from __future__ import annotations

import json
from typing import Any

from ....shared.kernel.errors import ErrorCode, ValidationError
from ....shared.kernel.audit import AuditEvent
from ...conversation.application.ports import GuardrailGateway
from ..domain.models import DataAnalysisAnswer, DatasetResult, QuerySpec


class DataQueryService:
    """Shared SQL/API query execution used by reports and interactive analysis."""

    def __init__(self, *, onequery_gateway, api_gateway=None) -> None:
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
        data_catalog_gateway,
        knowledge_gateway,
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

    def query_data(self, *, question: str, user_id: str) -> DataAnalysisAnswer:
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
        data = self.query_service.execute_sql(
            query=spec.sql,
            context={"lineage.tracing.enable": True, "scenario": "query_data"},
            user_id=user_id,
        )
        components = _visualization_components(data)
        answer = DataAnalysisAnswer(
            summary=self._summarize(question=question, spec=spec, data=data),
            query_spec=spec,
            data=data,
            components=components,
            warnings=list(data.warnings),
        )
        self._audit(
            AuditEvent(
                operation="data_analysis.query",
                detail=f"completed rows={len(data.rows)}",
                user_id=user_id,
                target_obj="query_data",
            )
        )
        return answer

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
