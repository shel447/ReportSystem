import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend.routers.parameter_options import ParameterOptionsResolveRequest, resolve_parameter_options


class ParameterOptionsRouterTests(unittest.TestCase):
    def test_resolve_parameter_options_returns_formal_option_payload(self):
        fake_service = type(
            "FakeService",
            (),
            {
                "resolve": lambda self, **_kwargs: {
                    "options": [{"display": "总部网络", "value": "hq-network", "query": "scope_id = 'hq-network'"}],
                    "defaultValue": [],
                }
            },
        )()

        with patch("backend.routers.parameter_options.build_parameter_option_service", return_value=fake_service):
            payload = resolve_parameter_options(
                ParameterOptionsResolveRequest(
                    parameterId="scope",
                    openSource={"url": "https://example.internal/api/network/scopes/options"},
                    contextValues={
                        "report_date": [
                            {"display": "2026-04-18", "value": "2026-04-18", "query": "2026-04-18"}
                        ]
                    },
                ),
                db=None,
                user_id="default",
            )

        self.assertEqual(payload["options"][0]["display"], "总部网络")
        self.assertEqual(payload["options"][0]["query"], "scope_id = 'hq-network'")

    def test_resolve_parameter_options_maps_validation_error_to_http_400(self):
        fake_service = type(
            "FakeService",
            (),
            {"resolve": lambda self, **_kwargs: (_ for _ in ()).throw(ValueError("invalid parameter option request"))},
        )()

        with patch("backend.routers.parameter_options.build_parameter_option_service", return_value=fake_service):
            with self.assertRaises(HTTPException) as ctx:
                resolve_parameter_options(
                    ParameterOptionsResolveRequest(
                        parameterId="scope",
                        openSource={"url": "https://example.internal/api/network/scopes/options"},
                        contextValues={},
                    ),
                    db=None,
                    user_id="default",
                )

        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
