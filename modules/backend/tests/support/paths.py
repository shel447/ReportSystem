from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
TESTDATA_DIR = PROJECT_ROOT / "testdata"


def testdata_path(*parts: str) -> Path:
    return TESTDATA_DIR.joinpath(*parts)
