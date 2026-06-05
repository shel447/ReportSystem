from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_external_policy_auth_for_unit_tests(monkeypatch):
    monkeypatch.setenv("REPORT_POLICY_AUTH_DISABLED", "1")
