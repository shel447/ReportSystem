from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from backend.infrastructure.ai.openai_compat import ProviderConfig
from backend.infrastructure.query.engine import QueryRequest, run_query
from backend.infrastructure.query.section_evidence import generate_section_evidence


class FakeGateway:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat_completion(self, config, messages, *, temperature=None, max_tokens=None):
        if not self.responses:
            raise AssertionError("No more fake responses configured")
        self.calls.append(
            {
                "model": config.model,
                "messages": list(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        response = self.responses.pop(0)
        return {
            "content": response,
            "model": config.model,
            "raw": {},
        }


class QueryEngineTests(unittest.TestCase):
    def setUp(self):
        self.config = ProviderConfig(
            base_url="http://example.invalid",
            model="test-model",
            api_key="test-key",
            timeout_sec=30,
            temperature=0.2,
        )
        self.request = QueryRequest(
            nl_request="请查询站点名称列表，只保留前 2 条。",
            template_context={
                "name": "测试模板",
                "description": "测试描述",
                "category": "operations",
            },
            section={
                "title": "站点列表",
                "description": "查询站点",
            },
            params={"date": "2026-03-06"},
        )

    def test_run_query_single_pass_strategy_uses_single_generation_step(self):
        gateway = FakeGateway(
            [
                'result = tables["dim_site"].select("site_name").limit(2)',
            ]
        )

        result = run_query(
            gateway=gateway,
            config=self.config,
            request=self.request,
            strategy="single_pass",
        )

        self.assertEqual(result.debug["strategy"], "single_pass")
        self.assertEqual(result.debug["attempts"], 1)
        self.assertEqual(result.debug["query_spec"], {})
        self.assertIn("dim_site", result.compiled_sql)
        self.assertEqual(len(gateway.calls), 1)

    def test_run_query_ibis_planner_returns_query_spec_and_schema_candidates(self):
        gateway = FakeGateway(
            [
                """
                {
                  "intent": "list_sites",
                  "tables": ["dim_site"],
                  "joins": [],
                  "dimensions": ["site_name"],
                  "measures": [],
                  "filters": [],
                  "sort": [],
                  "limit": 2,
                  "notes": [],
                  "warnings": []
                }
                """,
                'result = tables["dim_site"].select("site_name").limit(2)',
            ]
        )

        result = run_query(
            gateway=gateway,
            config=self.config,
            request=self.request,
            strategy="ibis_planner",
        )

        self.assertEqual(result.debug["strategy"], "ibis_planner")
        self.assertEqual(result.debug["query_spec"]["intent"], "list_sites")
        self.assertTrue(result.debug["schema_candidates"])
        self.assertEqual(result.debug["attempts"], 1)
        self.assertIn("dim_site", result.compiled_sql)
        self.assertEqual(len(gateway.calls), 2)

    def test_run_query_ibis_planner_retries_code_generation_after_failure(self):
        gateway = FakeGateway(
            [
                """
                {
                  "intent": "list_sites",
                  "tables": ["dim_site"],
                  "joins": [],
                  "dimensions": ["site_name"],
                  "measures": [],
                  "filters": [],
                  "sort": [],
                  "limit": 2,
                  "notes": [],
                  "warnings": []
                }
                """,
                'result = tables["missing_table"].select("site_name").limit(2)',
                'result = tables["dim_site"].select("site_name").limit(2)',
            ]
        )

        result = run_query(
            gateway=gateway,
            config=self.config,
            request=self.request,
            strategy="ibis_planner",
        )

        self.assertEqual(result.debug["attempts"], 2)
        self.assertEqual(result.debug["error_stage"], "")
        self.assertIn("dim_site", result.compiled_sql)
        self.assertEqual(len(gateway.calls), 3)


class SectionQueryServiceStrategyTests(unittest.TestCase):
    def setUp(self):
        self.config = ProviderConfig(
            base_url="http://example.invalid",
            model="test-model",
            api_key="test-key",
            timeout_sec=30,
            temperature=0.2,
        )
        self.template_context = {
            "name": "设备巡检报告",
            "description": "每日巡检",
            "category": "operations",
        }
        self.section = {"title": "站点列表", "description": "查询站点"}

    def test_generate_section_evidence_uses_internal_strategy_switch(self):
        gateway = FakeGateway(
            [
                """
                {
                  "intent": "list_sites",
                  "tables": ["dim_site"],
                  "joins": [],
                  "dimensions": ["site_name"],
                  "measures": [],
                  "filters": [],
                  "sort": [],
                  "limit": 2,
                  "notes": [],
                  "warnings": []
                }
                """,
                'result = tables["dim_site"].select("site_name").limit(2)',
            ]
        )

        with patch.dict(os.environ, {"REPORT_QUERY_STRATEGY": "ibis_planner"}, clear=False):
            evidence = generate_section_evidence(
                gateway=gateway,
                config=self.config,
                template_context=self.template_context,
                section=self.section,
                params={},
            )

        self.assertEqual(evidence["data_status"], "success")
        self.assertEqual(evidence["debug"]["strategy"], "ibis_planner")
        self.assertIn("query_spec", evidence["debug"])
        self.assertIn("schema_candidates", evidence["debug"])
        self.assertIn("compiled_sql", evidence["debug"])


if __name__ == "__main__":
    unittest.main()
