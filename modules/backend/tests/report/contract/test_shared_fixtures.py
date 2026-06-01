from __future__ import annotations

from src.contexts.report.infrastructure.template_schema import ReportDslSchemaGateway
from src.contexts.report.infrastructure.template_repositories import TemplateSchemaGateway
from tests.support.builders import load_json_fixture


def test_shared_flow_and_paged_report_dsl_fixtures_match_formal_schema():
    for name in ("showcase-flow.json", "showcase-paged.json"):
        assert ReportDslSchemaGateway().validate_report(load_json_fixture("report-dsl", name))


def test_shared_flow_and_paged_template_fixtures_match_formal_schema():
    gateway = TemplateSchemaGateway()
    for name in (
        "network-daily-flow.json",
        "network-summary-paged.json",
        "network-device-health-inspection-flow.json",
        "network-device-health-inspection-paged.json",
        "network-operations-status-flow.json",
        "network-operations-status-paged.json",
    ):
        assert gateway.validate(load_json_fixture("report-templates", name))
