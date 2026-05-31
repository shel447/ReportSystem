import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ...shared.kernel.paths import report_system_db_path
from .upgrades import apply_upgrades

try:
    from sqlalchemy.orm import DeclarativeBase
except ImportError:
    DeclarativeBase = None

DB_PATH = os.fspath(report_system_db_path())
DATABASE_URL = f"sqlite:///{DB_PATH}"
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

if DeclarativeBase is not None:
    class Base(DeclarativeBase):
        pass
else:
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models  # noqa: F401
    from .dev_database import init_dev_db
    from ..demo.telecom import init_telecom_demo_db

    apply_upgrades(
        database_path=Path(DB_PATH),
        upgrades_dir=Path(__file__).with_name("upgrades"),
        engine=engine,
        metadata=Base.metadata,
    )
    init_dev_db()
    init_telecom_demo_db()
