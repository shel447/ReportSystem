from __future__ import annotations

import pytest

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


def test_dataset_response_schema_accepts_new_success_and_business_error_envelopes():
    gateway = ReportDslSchemaGateway()
    success = {
        "retCode": 0,
        "retInfo": "",
        "data": {
            "columns": {
                "health_score": {
                    "type": "number",
                    "lineageTracing": {
                        "type": "original",
                        "sources": [
                            {
                                "dataSourceName": "network_health",
                                "dataSourceType": "logicalEntity",
                                "field": "health_score",
                                "businessName": "Health Score",
                                "businessName_cn": "健康评分",
                                "enumValues": "",
                                "ui": "",
                            }
                        ],
                    },
                }
            },
            "results": [{"health_score": 96}],
        },
    }

    assert gateway.validate_dataset_response(success) == success
    no_lineage = {
        "retCode": 0,
        "retInfo": "",
        "data": {"columns": {"health_score": {"type": "number"}}, "results": []},
    }
    assert gateway.validate_dataset_response(no_lineage) == no_lineage
    assert gateway.validate_dataset_response({"retCode": 1001, "retInfo": "query failed"}) == {
        "retCode": 1001,
        "retInfo": "query failed",
    }


def test_dataset_response_schema_rejects_legacy_result_set_envelope():
    with pytest.raises(ValueError, match="数据集响应校验失败"):
        ReportDslSchemaGateway().validate_dataset_response(
            {"data": {"results": [{"columns": [], "results": []}]}}
        )


def test_dataset_response_schema_rejects_success_without_data():
    with pytest.raises(ValueError, match="数据集响应校验失败"):
        ReportDslSchemaGateway().validate_dataset_response({"retCode": 0, "retInfo": ""})
