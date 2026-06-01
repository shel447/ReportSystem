from pathlib import Path
import shutil
import sqlite3

import pytest
from sqlalchemy import create_engine, inspect

from src.infrastructure.persistence.database import Base
from src.infrastructure.persistence.dev_database import DevBase
from src.infrastructure.persistence import dev_models, models  # noqa: F401
from src.infrastructure.persistence.upgrades import DatabaseUpgradeError, apply_upgrades


PERSISTENCE_DIR = Path(__file__).resolve().parents[3] / "src" / "infrastructure" / "persistence"
BUSINESS_UPGRADES = PERSISTENCE_DIR / "upgrades"
DEV_UPGRADES = BUSINESS_UPGRADES / "dev"


def _engine(path: Path):
    return create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})


def test_business_upgrades_create_current_schema_and_are_idempotent(tmp_path):
    db_path = tmp_path / "report-system.db"
    engine = _engine(db_path)

    assert apply_upgrades(database_path=db_path, upgrades_dir=BUSINESS_UPGRADES, engine=engine, metadata=Base.metadata) == 3
    assert apply_upgrades(database_path=db_path, upgrades_dir=BUSINESS_UPGRADES, engine=engine, metadata=Base.metadata) == 3

    inspector = inspect(engine)
    assert set(Base.metadata.tables) <= set(inspector.get_table_names())
    assert {"user_id"} <= {item["name"] for item in inspector.get_columns("tbl_export_jobs")}
    assert "ix_tbl_export_jobs_user_id" in {item["name"] for item in inspector.get_indexes("tbl_export_jobs")}
    assert "tbl_chats" not in inspector.get_table_names()
    assert "tbl_conversations" not in inspector.get_table_names()
    assert {
        ("user_id", "tbl_users", "id"),
    } <= {
        (item["constrained_columns"][0], item["referred_table"], item["referred_columns"][0])
        for item in inspector.get_foreign_keys("tbl_export_jobs")
    }
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT current_version FROM __db_schema_version WHERE id = 1").fetchone() == (3,)


def test_dev_upgrades_create_separate_development_schema(tmp_path):
    db_path = tmp_path / "dev-support.db"
    engine = _engine(db_path)

    assert apply_upgrades(database_path=db_path, upgrades_dir=DEV_UPGRADES, engine=engine, metadata=DevBase.metadata) == 1

    assert set(inspect(engine).get_table_names()) == {
        "__db_schema_version",
        "dev_feedbacks",
        "dev_system_settings",
    }


def test_upgrade_rejects_database_version_newer_than_code(tmp_path):
    db_path = tmp_path / "future.db"
    engine = _engine(db_path)
    apply_upgrades(database_path=db_path, upgrades_dir=BUSINESS_UPGRADES, engine=engine, metadata=Base.metadata)
    with sqlite3.connect(db_path) as connection:
        connection.execute("UPDATE __db_schema_version SET current_version = 999 WHERE id = 1")
        connection.commit()

    with pytest.raises(DatabaseUpgradeError, match="newer than supported"):
        apply_upgrades(database_path=db_path, upgrades_dir=BUSINESS_UPGRADES, engine=engine, metadata=Base.metadata)


def test_upgrade_rejects_version_gaps(tmp_path):
    upgrades_dir = tmp_path / "upgrades"
    upgrades_dir.mkdir()
    shutil.copy(BUSINESS_UPGRADES / "V000__initialize_database_version.sql", upgrades_dir)
    shutil.copy(
        BUSINESS_UPGRADES / "V001__initialize_business_tables.sql",
        upgrades_dir / "V002__initialize_business_tables.sql",
    )

    with pytest.raises(DatabaseUpgradeError, match="continuous"):
        apply_upgrades(
            database_path=tmp_path / "gap.db",
            upgrades_dir=upgrades_dir,
            engine=_engine(tmp_path / "gap.db"),
            metadata=Base.metadata,
        )


def test_upgrade_rejects_unversioned_schema_drift(tmp_path):
    db_path = tmp_path / "drift.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE tbl_users (id VARCHAR PRIMARY KEY)")
        connection.commit()
    engine = _engine(db_path)

    with pytest.raises(DatabaseUpgradeError, match="schema drift"):
        apply_upgrades(database_path=db_path, upgrades_dir=BUSINESS_UPGRADES, engine=engine, metadata=Base.metadata)


def test_gitignore_marks_runtime_directory_as_ignored():
    gitignore_path = Path(__file__).resolve().parents[5] / ".gitignore"
    gitignore_text = gitignore_path.read_text(encoding="utf-8")

    assert ".runtime/" in gitignore_text
    assert ".test/" in gitignore_text
