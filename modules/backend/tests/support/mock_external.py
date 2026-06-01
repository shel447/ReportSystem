"""Fixture-backed external business gateway for report development tests."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from src.contexts.data_analysis.domain.models import DatasetColumn, DatasetResult
from src.contexts.report.application.custom_content_resolver import CustomContentResolver
from src.contexts.report.application.dataset_execution_service import DatasetExecutionService
from src.contexts.report.domain.generation_models import ReportDsl, report_dsl_to_dict
from src.contexts.report.domain.report_dsl_compiler import ReportDslCompiler
from src.contexts.report.domain.template_instance_builder import instantiate_template_instance, serialize_template_instance
from src.contexts.report.domain.template_models import report_template_from_dict
from src.contexts.report.infrastructure.template_schema import ReportDslSchemaGateway, validate_template_instance
from src.shared.kernel.errors import UpstreamError

from .builders import load_json_fixture


COMPLEX_TEMPLATE_FIXTURES = (
    "network-device-health-inspection-flow.json",
    "network-device-health-inspection-paged.json",
    "network-operations-status-flow.json",
    "network-operations-status-paged.json",
)


@dataclass
class FixtureExternalBusinessGateway:
    fixtures: dict[str, Any] = field(default_factory=lambda: load_json_fixture("mock-server", "responses.json"))
    requests: list[dict[str, Any]] = field(default_factory=list)

    def post_json(self, *, path_or_url: str | None = None, url: str | None = None, payload: dict[str, Any], user_id: str):
        path = str(path_or_url or url or "")
        self.requests.append({"path": path, "payload": copy.deepcopy(payload), "user_id": user_id})
        if path == "/rest/dte/v1/onequery/uql/query":
            query = str(payload.get("query") or "").lower()
            key = next((item for item in self.fixtures["queryMatches"] if item in query), "default")
            return _dataset_response(self.fixtures["datasets"][key])
        if path.startswith("/rest/datasets/"):
            return _dataset_response(self.fixtures["datasets"][path.rsplit("/", 1)[-1]])
        if path.startswith("/rest/dynamic-content/"):
            return copy.deepcopy(self.fixtures["dynamicContent"][path.rsplit("/", 1)[-1]])
        if path.startswith("/rest/parameter-options/"):
            return copy.deepcopy(self.fixtures["parameterOptions"][path.rsplit("/", 1)[-1]])
        raise AssertionError(f"unexpected fixture external request: {path}")


@dataclass
class FixtureDataQueryService:
    gateway: FixtureExternalBusinessGateway

    def execute_sql(self, *, query: str, context: dict[str, Any], user_id: str) -> DatasetResult:
        return _dataset_result(
            self.gateway.post_json(
                path_or_url="/rest/dte/v1/onequery/uql/query",
                payload={"query": query, "context": context},
                user_id=user_id,
            )
        )

    def execute_api(self, *, source: str, payload: dict[str, Any], user_id: str) -> DatasetResult:
        return _dataset_result(self.gateway.post_json(path_or_url=source, payload=payload, user_id=user_id))


def compile_complex_template(name: str, *, gateway: FixtureExternalBusinessGateway | None = None) -> ReportDsl:
    external = gateway or FixtureExternalBusinessGateway()
    schema = ReportDslSchemaGateway()
    template = report_template_from_dict(load_json_fixture("report-templates", name))
    instance = instantiate_template_instance(
        instance_id=f"ti_{template.id}",
        template=template,
        conversation_id="conv_fixture",
        chat_id="chat_fixture",
        status="ready_for_confirmation",
        capture_stage="confirm_params",
        revision=1,
        parameter_values={},
    )
    validate_template_instance(serialize_template_instance(instance))
    custom = CustomContentResolver(gateway=external, schema_gateway=schema).resolve(
        template_instance=instance,
        user_id="fixture-user",
    )
    datasets = DatasetExecutionService(query_service=FixtureDataQueryService(external), schema_gateway=schema).resolve(
        template_instance=instance,
        user_id="fixture-user",
    )
    report = ReportDslCompiler().compile(
        report_id=f"rpt_{template.id}",
        template=template,
        template_instance=instance,
        dataset_results=datasets,
        custom_catalogs=custom.catalogs,
        custom_sections=custom.sections,
        custom_slides=custom.slides,
        custom_components=custom.components,
    )
    schema.validate_report(report_dsl_to_dict(report))
    return report


def _dataset_response(dataset: dict[str, Any]) -> dict[str, Any]:
    return {"retCode": 0, "retInfo": "", "data": copy.deepcopy(dataset)}


def _dataset_result(payload: dict[str, Any]) -> DatasetResult:
    if "retCode" not in payload:
        raise UpstreamError("dataset response retCode is required")
    ret_code = int(payload["retCode"])
    if ret_code != 0:
        raise UpstreamError(str(payload.get("retInfo") or "dataset query failed"), details={"retCode": ret_code})
    data = payload.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("columns"), dict) or not isinstance(data.get("results"), list):
        raise UpstreamError("dataset response data.columns/data.results is required")
    return DatasetResult(
        columns=[
            DatasetColumn(key=str(key), metadata=copy.deepcopy(metadata if isinstance(metadata, dict) else {}))
            for key, metadata in data["columns"].items()
        ],
        rows=copy.deepcopy(data["results"]),
    )
