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


@pytest.mark.parametrize("validate_response", ["validate_onequery_response", "validate_api_dataset_response"])
def test_query_response_schemas_accept_new_success_and_business_error_envelopes(validate_response):
    gateway = ReportDslSchemaGateway()
    validate = getattr(gateway, validate_response)
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

    assert validate(success) == success
    no_lineage = {
        "retCode": 0,
        "retInfo": "",
        "data": {"columns": {"health_score": {"type": "number"}}, "results": []},
    }
    assert validate(no_lineage) == no_lineage
    assert validate({"retCode": 1001, "retInfo": "query failed"}) == {
        "retCode": 1001,
        "retInfo": "query failed",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"retCode": "04003", "retInfo": "dblink does not support connect by"},
        {"retCode": "04023", "retInfo": "query field does not exist"},
    ],
)
def test_onequery_schema_preserves_known_string_business_error_codes(payload):
    assert ReportDslSchemaGateway().validate_onequery_response(payload) == payload
    with pytest.raises(ValueError, match="响应校验失败"):
        ReportDslSchemaGateway().validate_api_dataset_response(payload)


@pytest.mark.parametrize("validate_response", ["validate_onequery_response", "validate_api_dataset_response"])
def test_query_response_schemas_reject_legacy_result_set_envelope(validate_response):
    with pytest.raises(ValueError, match="响应校验失败"):
        getattr(ReportDslSchemaGateway(), validate_response)(
            {"data": {"results": [{"columns": [], "results": []}]}}
        )


@pytest.mark.parametrize("validate_response", ["validate_onequery_response", "validate_api_dataset_response"])
def test_query_response_schemas_reject_success_without_data(validate_response):
    with pytest.raises(ValueError, match="响应校验失败"):
        getattr(ReportDslSchemaGateway(), validate_response)({"retCode": 0, "retInfo": ""})
