import unittest
from unittest.mock import patch

import httpx

from src.contexts.report.application.parameter_service import ReportParameterService
from src.contexts.report.infrastructure.parameter_options import ParameterOptionsGateway
from src.contexts.report.domain.template_models import ParameterValue
from src.contexts.report.infrastructure.external_business import ExternalBusinessGateway
from src.shared.kernel.errors import ValidationError


class _FakeExternalBusinessGateway:
    def __init__(self):
        self.requests = []

    def post_json(self, *, path_or_url, payload, user_id):
        self.requests.append({"path_or_url": path_or_url, "payload": payload, "user_id": user_id})
        return {
            "options": [
                {"label": "总部网络", "value": "hq-network", "query": "scope_id = 'hq-network'"},
                {"label": "园区网络", "value": "campus-network", "query": "scope_id = 'campus-network'"},
            ],
            "defaultValue": [],
        }


class DynamicSourceServiceTests(unittest.TestCase):
    def test_parameter_option_service_calls_formal_external_source(self):
        external = _FakeExternalBusinessGateway()
        service = ReportParameterService(options_gateway=ParameterOptionsGateway(gateway=external))

        result = service.resolve(
            user_id="ops-user",
            parameter_id="scope",
            source="/rest/parameter-options/scopes",
            context_values={
                "reportDate": [
                    ParameterValue(label="2026-06-01", value="2026-06-01", query="'2026-06-01'")
                ]
            },
        )

        self.assertEqual(result.options[0].label, "总部网络")
        self.assertEqual(result.options[0].value, "hq-network")
        self.assertEqual(result.options[0].query, "scope_id = 'hq-network'")
        self.assertEqual(external.requests[0]["path_or_url"], "/rest/parameter-options/scopes")
        self.assertEqual(external.requests[0]["user_id"], "ops-user")
        self.assertEqual(external.requests[0]["payload"]["reportDate"][0]["value"], "2026-06-01")

    def test_hidden_local_api_shortcut_is_rejected(self):
        service = ReportParameterService()

        with self.assertRaises(ValidationError):
            service.resolve(
                user_id="default",
                parameter_id="scope",
                source="api:/sites/list",
                context_values={},
            )

    def test_external_gateway_joins_relative_url_and_sends_user_header(self):
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={"ok": True})

        transport = httpx.MockTransport(handler)
        client_type = httpx.Client
        with patch(
            "src.contexts.report.infrastructure.external_business.httpx.Client",
            side_effect=lambda **kwargs: client_type(transport=transport, **kwargs),
        ):
            result = ExternalBusinessGateway(base_url="http://mock.example").post_json(
                path_or_url="/rest/datasets/network-health",
                payload={"parameters": {}},
                user_id="ops-user",
            )

        self.assertEqual(result, {"ok": True})
        self.assertEqual(str(requests[0].url), "http://mock.example/rest/datasets/network-health")
        self.assertEqual(requests[0].headers["X-User-Id"], "ops-user")


if __name__ == "__main__":
    unittest.main()
