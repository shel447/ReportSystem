from __future__ import annotations

from src.contexts.report.application.generation_service import REPORT_VALIDATOR
from src.contexts.report.infrastructure.template_repositories import TemplateSchemaGateway
from tests.support.builders import load_json_fixture


def test_shared_flow_and_paged_report_dsl_fixtures_match_formal_schema():
    for name in ("showcase-flow.json", "showcase-paged.json"):
        errors = sorted(
            REPORT_VALIDATOR.iter_errors(load_json_fixture("report-dsl", name)),
            key=lambda error: list(error.path),
        )
        assert errors == []


def test_shared_flow_and_paged_template_fixtures_match_formal_schema():
    gateway = TemplateSchemaGateway()
    for name in ("network-daily-flow.json", "network-summary-paged.json"):
        assert gateway.validate(load_json_fixture("report-templates", name))
