"""Local development implementation of Runtime-managed named instances."""

from __future__ import annotations

import os
import threading
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .db import TableBase

_INSTANCES: dict[str, "ZenithInstance"] = {}
_INSTANCES_LOCK = threading.RLock()
_BUSINESS_INSTANCE = "dtesmartbiservicedb"


class ZenithInstance:
    """Lazy local database instance compatible with the platform Runtime."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._lock = threading.RLock()
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None

    def session(self) -> Session:
        with self._lock:
            if self._engine is None or self._session_factory is None:
                database_path = _database_path(self.name)
                database_path.parent.mkdir(parents=True, exist_ok=True)
                self._engine = create_engine(
                    f"sqlite:///{database_path}",
                    connect_args={"check_same_thread": False},
                )
                self._session_factory = sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=self._engine,
                )
            TableBase.metadata.create_all(bind=self._engine)
            return self._session_factory()


def zenith_instance(name: str) -> ZenithInstance:
    """Return the stable Runtime instance registered under ``name``."""

    normalized = str(name or "").strip()
    if not normalized:
        raise ValueError("instance name is required")
    with _INSTANCES_LOCK:
        instance = _INSTANCES.get(normalized)
        if instance is None:
            instance = ZenithInstance(normalized)
            _INSTANCES[normalized] = instance
        return instance


def _database_path(name: str) -> Path:
    data_dir = _runtime_data_dir()
    filename = "report_system.db" if name == _BUSINESS_INSTANCE else f"{name}.db"
    return data_dir / filename


def _runtime_data_dir() -> Path:
    configured = os.getenv("RUNTIME_DB_DIR")
    if configured:
        path = Path(configured).expanduser()
        return path if path.is_absolute() else Path.cwd() / path
    for candidate in (Path.cwd(), *Path.cwd().parents):
        if (candidate / ".git").exists():
            return candidate / ".runtime"
    return Path.cwd() / ".runtime"
