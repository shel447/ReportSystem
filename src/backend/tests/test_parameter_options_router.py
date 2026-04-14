import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend.contexts.template_catalog.application.parameter_options import ParameterOptionService
from backend.routers.parameter_options import ParameterOptionsResolveRequest, resolve_parameter_options


class ParameterOptionsRouterTests(unittest.TestCase):
    def test_resolve_parameter_options_returns_label_value_query_items(self):
        with patch("backend.routers.parameter_options.build_parameter_option_service") as build_service:
            build_service.return_value.resolve.return_value = {
                "items": [{"label": "华东一大区", "value": "EAST_1", "query": "EAST_1"}],
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
        self.assertEqual(payload["items"][0]["query"], "EAST_1")

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


class ParameterOptionServiceTests(unittest.TestCase):
    def test_resolve_demo_source_returns_query_channel(self):
        payload = ParameterOptionService().resolve(
            user_id="default",
            template_id="tpl-1",
            param_id="region",
            source="api:/devices/list",
            limit=2,
        )

        self.assertTrue(payload["items"])
        self.assertIn("query", payload["items"][0])

    def test_resolve_http_source_returns_empty_items_when_query_channel_missing(self):
        service = ParameterOptionService()

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"items": [{"label": "华东一大区", "value": "EAST_1"}], "has_more": False}

        class FakeClient:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def post(self, *_args, **_kwargs):
                return FakeResponse()

        with patch("backend.contexts.template_catalog.application.parameter_options.httpx.Client", return_value=FakeClient()):
            payload = service.resolve(
                user_id="default",
                template_id="tpl-1",
                param_id="region",
                source="https://example.com/regions",
                limit=2,
            )

        self.assertEqual(payload["items"], [])
        self.assertEqual(payload["meta"]["error_code"], "PARAM_SOURCE_RESPONSE_INVALID")


if __name__ == "__main__":
    unittest.main()
