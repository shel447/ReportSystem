"""Fixture-backed external business gateway for report development tests."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from src.contexts.report.application.custom_content_resolver import CustomContentResolver
from src.contexts.report.application.dataset_execution_service import DatasetExecutionService
from src.contexts.report.domain.generation_models import ReportDsl, report_dsl_to_dict
from src.contexts.report.domain.report_dsl_compiler import ReportDslCompiler
from src.contexts.report.domain.template_instance_builder import instantiate_template_instance, serialize_template_instance
from src.contexts.report.domain.template_models import report_template_from_dict
from src.contexts.report.infrastructure.template_schema import ReportDslSchemaGateway, validate_template_instance

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
        if path == "/rest/onequery":
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
    datasets = DatasetExecutionService(gateway=external, schema_gateway=schema).resolve(
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
