from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List

from ..ai.openai_compat import OpenAICompatGateway, ProviderConfig
from .engine import QueryRequest, QueryRunResult, run_query

BENCHMARK_CASES_PATH = os.path.join(os.path.dirname(__file__), "benchmarks", "query_cases.json")


def load_benchmark_cases(path: str | None = None) -> List[Dict[str, Any]]:
    target = path or BENCHMARK_CASES_PATH
    with open(target, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError("Benchmark cases must be a JSON array.")
    return [item for item in payload if isinstance(item, dict)]


def run_query_benchmark(
    *,
    gateway: OpenAICompatGateway,
    config: ProviderConfig,
    strategy: str,
    cases: List[Dict[str, Any]] | None = None,
    query_runner: Callable[..., QueryRunResult] = run_query,
) -> Dict[str, Any]:
    benchmark_cases = cases or load_benchmark_cases()
    results: List[Dict[str, Any]] = []
    passed = 0
    for case in benchmark_cases:
        request = QueryRequest(
            nl_request=str(case.get("question") or "").strip(),
            template_context={"name": "benchmark", "description": "", "report_type": "benchmark", "scenario": "benchmark"},
            section={"title": str(case.get("category") or "benchmark"), "description": str(case.get("question") or "")},
            params={},
        )
        result = query_runner(
            gateway=gateway,
            config=config,
            request=request,
            strategy=strategy,
        )
        evaluation = evaluate_benchmark_case(case, result)
        if evaluation["passed"]:
            passed += 1
        results.append(
            {
                "case_id": case.get("case_id"),
                "strategy": strategy,
                "passed": evaluation["passed"],
                "checks": evaluation["checks"],
                "compiled_sql": result.compiled_sql,
                "row_count": result.row_count,
                "error_message": result.debug.get("error_message") or "",
            }
        )
    total = len(results)
    return {
        "strategy": strategy,
        "total": total,
        "passed": passed,
        "failed": max(0, total - passed),
        "pass_rate": round((passed / total), 4) if total else 0.0,
        "results": results,
    }


def evaluate_benchmark_case(case: Dict[str, Any], result: QueryRunResult) -> Dict[str, Any]:
    sql = str(result.compiled_sql or "").upper()
    checks: List[Dict[str, Any]] = []

    for table in case.get("expected_tables") or []:
        token = str(table or "").upper()
        checks.append(
            {
                "type": "table",
                "expected": token,
                "passed": token in sql,
            }
        )

    for feature in case.get("expected_sql_features") or []:
        token = str(feature or "").upper()
        checks.append(
            {
                "type": "sql_feature",
                "expected": token,
                "passed": token in sql,
            }
        )

    if not checks:
        checks.append({"type": "non_empty_sql", "expected": "compiled_sql", "passed": bool(sql)})

    return {
        "passed": all(item["passed"] for item in checks) and bool(result.success),
        "checks": checks,
    }
