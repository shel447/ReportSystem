from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

try:
    from sqlalchemy.orm import DeclarativeBase
except ImportError:
    DeclarativeBase = None

DB_PATH = os.path.join(os.path.dirname(__file__), "report_system.db")
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
    from .telecom_demo_service import init_telecom_demo_db
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns()
    init_telecom_demo_db()


def _ensure_sqlite_columns():
    additions = {
        "report_templates": {
            "match_keywords": "JSON DEFAULT '[]'",
            "template_type": "TEXT DEFAULT ''",
            "scene": "TEXT DEFAULT ''",
            "parameters": "JSON DEFAULT '[]'",
            "sections": "JSON DEFAULT '[]'",
            "schema_version": "TEXT DEFAULT ''",
        },
        "chat_sessions": {
            "title": "TEXT DEFAULT ''",
            "fork_meta": "JSON DEFAULT '{}'",
        },
        "scheduled_tasks": {
            "use_schedule_time_as_report_time": "BOOLEAN DEFAULT 0",
        },
        "report_instances": {
            "report_time": "DATETIME",
            "report_time_source": "TEXT DEFAULT ''",
        },
    }
    with engine.begin() as connection:
        for table_name, columns in additions.items():
            existing = {
                row[1]
                for row in connection.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()
            }
            for column_name, column_sql in columns.items():
                if column_name in existing:
                    continue
                connection.exec_driver_sql(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}"
                )
