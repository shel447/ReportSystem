"""Small canonical builders for tests that need formal Report DSL objects."""

from __future__ import annotations

import json
from typing import Any

from src.contexts.report.domain.generation_models import ReportDsl, report_dsl_from_dict

from .paths import testdata_path


def load_json_fixture(*parts: str) -> dict[str, Any]:
    return json.loads(testdata_path(*parts).read_text(encoding="utf-8"))


def build_flow_report(**overrides: Any) -> ReportDsl:
    payload = load_json_fixture("report-dsl", "showcase-flow.json")
    payload.update(overrides)
    return report_dsl_from_dict(payload)


def build_paged_report(**overrides: Any) -> ReportDsl:
    payload = load_json_fixture("report-dsl", "showcase-paged.json")
    payload.update(overrides)
    return report_dsl_from_dict(payload)
