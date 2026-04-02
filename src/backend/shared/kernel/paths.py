from __future__ import annotations

from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def backend_root() -> Path:
    return BACKEND_ROOT


def report_system_db_path() -> Path:
    return BACKEND_ROOT / "report_system.db"


def telecom_demo_db_path() -> Path:
    return BACKEND_ROOT / "telecom_demo.db"
