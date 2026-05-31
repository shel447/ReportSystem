"""Backend test bootstrap: isolate generated data from deployment runtime files."""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_RUN_DIR = PROJECT_ROOT / ".test" / "runs" / f"pytest-{uuid.uuid4().hex[:12]}"
TEST_RUN_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("REPORT_SYSTEM_DATA_DIR", str(TEST_RUN_DIR))


def pytest_sessionfinish(session, exitstatus) -> None:
    if os.environ.get("REPORT_SYSTEM_KEEP_TEST_OUTPUTS") == "1":
        return
    shutil.rmtree(TEST_RUN_DIR, ignore_errors=True)
    for directory in (TEST_RUN_DIR.parent, TEST_RUN_DIR.parent.parent):
        try:
            directory.rmdir()
        except OSError:
            break
