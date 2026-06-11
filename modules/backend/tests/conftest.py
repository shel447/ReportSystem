from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_external_policy_auth_for_unit_tests(monkeypatch):
    monkeypatch.setenv("REPORT_POLICY_AUTH_DISABLED", "1")
    monkeypatch.setenv("CHATBI_COMPLETION_BASE_URL", "http://127.0.0.1:8310/v1")
    monkeypatch.setenv("CHATBI_COMPLETION_MODEL", "mock-chat")
    monkeypatch.setenv("CHATBI_COMPLETION_API_KEY", "mock-key")
    monkeypatch.setenv("CHATBI_EMBEDDING_BASE_URL", "http://127.0.0.1:8310/v1")
    monkeypatch.setenv("CHATBI_EMBEDDING_MODEL", "mock-embedding")
    monkeypatch.setenv("CHATBI_EMBEDDING_API_KEY", "mock-key")
    monkeypatch.setenv("CHATBI_EMBEDDING_USE_COMPLETION_AUTH", "false")
