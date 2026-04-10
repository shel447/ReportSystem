import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend.routers.parameter_options import ParameterOptionsResolveRequest, resolve_parameter_options


class ParameterOptionsRouterTests(unittest.TestCase):
    def test_resolve_parameter_options_returns_label_value_items(self):
        with patch("backend.routers.parameter_options.build_parameter_option_service") as build_service:
            build_service.return_value.resolve.return_value = {
                "items": [{"label": "华东一大区", "value": "EAST_1"}],
                "meta": {"source": "api:/devices/list", "limit": 10, "returned": 1, "has_more": False, "truncated": False},
            }

            payload = resolve_parameter_options(
                ParameterOptionsResolveRequest(
                    template_id="tpl-1",
                    param_id="region",
                    source="api:/devices/list",
                    query="华东",
                    selected_params={"scene": "总部"},
                    limit=10,
                ),
                db=None,
                user_id="default",
            )

        self.assertEqual(payload["items"][0]["label"], "华东一大区")
        self.assertEqual(payload["items"][0]["value"], "EAST_1")

    def test_resolve_parameter_options_maps_validation_error_to_http_400(self):
        with patch("backend.routers.parameter_options.build_parameter_option_service") as build_service:
            build_service.return_value.resolve.side_effect = ValueError("limit too large")

            with self.assertRaises(HTTPException) as ctx:
                resolve_parameter_options(
                    ParameterOptionsResolveRequest(param_id="region", source="api:/devices/list"),
                    db=None,
                    user_id="default",
                )

        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
