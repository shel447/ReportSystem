from __future__ import annotations

import unittest

from backend.infrastructure.ai.openai_compat import ProviderConfig
from backend.infrastructure.query.benchmark import evaluate_benchmark_case, load_benchmark_cases, run_query_benchmark
from backend.infrastructure.query.engine import QueryRunResult


class FakeGateway:
    pass


class QueryBenchmarkServiceTests(unittest.TestCase):
    def setUp(self):
        self.config = ProviderConfig(
            base_url="http://example.invalid",
            model="test-model",
            api_key="test-key",
            timeout_sec=30,
            temperature=0.2,
        )

    def test_load_benchmark_cases_returns_seed_cases(self):
        cases = load_benchmark_cases()

        self.assertGreaterEqual(len(cases), 6)
        self.assertEqual(cases[0]["case_id"], "site-list-top2")

    def test_evaluate_benchmark_case_checks_expected_tables_and_features(self):
        result = QueryRunResult(
            success=True,
            model="test-model",
            compiled_sql="SELECT site_name FROM dim_site LIMIT 2",
            sample_rows=[{"site_name": "上海1号站"}],
            row_count=2,
            debug={"error_message": ""},
        )

        evaluation = evaluate_benchmark_case(
            {
                "expected_tables": ["dim_site"],
                "expected_sql_features": ["LIMIT 2"],
            },
            result,
        )

        self.assertTrue(evaluation["passed"])
        self.assertEqual(len(evaluation["checks"]), 2)

    def test_run_query_benchmark_summarizes_case_results(self):
        calls = []

        def fake_runner(*, gateway, config, request, strategy):
            calls.append((request.nl_request, strategy))
            return QueryRunResult(
                success=True,
                model="test-model",
                compiled_sql="SELECT site_name FROM dim_site LIMIT 2",
                sample_rows=[{"site_name": "上海1号站"}],
                row_count=2,
                debug={"error_message": ""},
            )

        report = run_query_benchmark(
            gateway=FakeGateway(),
            config=self.config,
            strategy="ibis_planner",
            cases=[
                {
                    "case_id": "case-1",
                    "question": "列出前2个站点名称",
                    "expected_tables": ["dim_site"],
                    "expected_sql_features": ["LIMIT 2"],
                }
            ],
            query_runner=fake_runner,
        )

        self.assertEqual(report["strategy"], "ibis_planner")
        self.assertEqual(report["total"], 1)
        self.assertEqual(report["passed"], 1)
        self.assertEqual(calls[0][1], "ibis_planner")


if __name__ == "__main__":
    unittest.main()
