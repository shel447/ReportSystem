"""Development-support SQLite database connection and initialization."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from ...shared.kernel.paths import dev_support_db_path
from .upgrades import apply_upgrades


DB_PATH = os.fspath(dev_support_db_path())
DATABASE_URL = f"sqlite:///{DB_PATH}"
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
DevSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class DevBase(DeclarativeBase):
    pass
def init_dev_db() -> None:
    from . import dev_models  # noqa: F401

    apply_upgrades(
        database_path=Path(DB_PATH),
        upgrades_dir=Path(__file__).with_name("upgrades") / "dev",
        engine=engine,
        metadata=DevBase.metadata,
    )
