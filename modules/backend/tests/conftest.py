from __future__ import annotations

import os
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_TEST_DATA_DIR = _PROJECT_ROOT / ".test" / "runs" / f"backend-pytest-{os.getpid()}"
os.environ.setdefault("REPORT_SYSTEM_DATA_DIR", str(_TEST_DATA_DIR))
os.environ.setdefault("RUNTIME_DB_DIR", str(_TEST_DATA_DIR))


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
