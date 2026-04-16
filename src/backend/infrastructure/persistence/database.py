import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ...shared.kernel.paths import report_system_db_path

try:
    from sqlalchemy.orm import DeclarativeBase
except ImportError:
    DeclarativeBase = None

DB_PATH = os.fspath(report_system_db_path())
DATABASE_URL = f"sqlite:///{DB_PATH}"

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
    from ..demo.telecom import init_telecom_demo_db

    Base.metadata.create_all(bind=engine)
    init_telecom_demo_db()
