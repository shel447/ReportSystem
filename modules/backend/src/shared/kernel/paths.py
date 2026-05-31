from __future__ import annotations

from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
BACKEND_MODULE_ROOT = BACKEND_ROOT.parents[0]
PROJECT_ROOT = BACKEND_ROOT.parents[2]


def backend_root() -> Path:
    return BACKEND_ROOT


def backend_module_root() -> Path:
    return BACKEND_MODULE_ROOT


def project_root() -> Path:
    return PROJECT_ROOT


def runtime_data_dir() -> Path:
    return PROJECT_ROOT / ".runtime"


def report_system_db_path() -> Path:
    return runtime_data_dir() / "report_system.db"


def dev_support_db_path() -> Path:
    return runtime_data_dir() / "dev_support.db"


def telecom_demo_db_path() -> Path:
    return runtime_data_dir() / "telecom_demo.db"
