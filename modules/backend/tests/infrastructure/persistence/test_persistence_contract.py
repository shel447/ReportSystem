from pathlib import Path
import shutil
import sqlite3

import pytest
from sqlalchemy import create_engine, inspect
from runtime.db import TableBase

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

    assert apply_upgrades(database_path=db_path, upgrades_dir=BUSINESS_UPGRADES, engine=engine, metadata=TableBase.metadata) == 4
    assert apply_upgrades(database_path=db_path, upgrades_dir=BUSINESS_UPGRADES, engine=engine, metadata=TableBase.metadata) == 4

    inspector = inspect(engine)
    assert set(TableBase.metadata.tables) <= set(inspector.get_table_names())
    assert {"user_id"} <= {item["name"] for item in inspector.get_columns("tbl_export_jobs")}
    assert "ix_tbl_export_jobs_user_id" in {item["name"] for item in inspector.get_indexes("tbl_export_jobs")}
    assert "tbl_chats" not in inspector.get_table_names()
    assert "tbl_conversations" not in inspector.get_table_names()
    assert "tbl_users" not in inspector.get_table_names()
    assert {
        (item["constrained_columns"][0], item["referred_table"], item["referred_columns"][0])
        for item in inspector.get_foreign_keys("tbl_export_jobs")
    } == {("report_instance_id", "tbl_report_instances", "id"), ("dependency_job_id", "tbl_export_jobs", "id")}
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT current_version FROM __db_schema_version WHERE id = 1").fetchone() == (4,)


def test_v004_removes_local_user_mirror_without_losing_owned_resources(tmp_path):
    legacy_upgrades = tmp_path / "legacy-upgrades"
    legacy_upgrades.mkdir()
    for version in range(4):
        source = next(BUSINESS_UPGRADES.glob(f"V{version:03d}__*.sql"))
        shutil.copy(source, legacy_upgrades / source.name)

    db_path = tmp_path / "legacy.db"
    engine = _engine(db_path)
    assert apply_upgrades(database_path=db_path, upgrades_dir=legacy_upgrades, engine=engine, metadata=TableBase.metadata) == 3
    with sqlite3.connect(db_path) as connection:
        connection.execute("INSERT INTO tbl_users (id, display_name, status, profile_json) VALUES ('external-user', 'Legacy', 'active', '{}')")
        connection.execute("INSERT INTO tbl_report_templates (id, category, name, description, schema_version, content) VALUES ('tpl', 'ops', 'Template', '', 'v1', '{}')")
        connection.execute("INSERT INTO tbl_template_instances (id, template_id, conversation_id, user_id, status, capture_stage, revision, schema_version, content) VALUES ('ti', 'tpl', 'conv', 'external-user', 'completed', 'report_ready', 1, 'v1', '{}')")
        connection.execute("INSERT INTO tbl_report_instances (id, template_id, template_instance_id, user_id, status, schema_version, content) VALUES ('rpt', 'tpl', 'ti', 'external-user', 'available', 'v1', '{}')")
        connection.execute("INSERT INTO tbl_report_documents (id, report_instance_id, artifact_kind, generation_mode, mime_type, storage_key, status) VALUES ('doc', 'rpt', 'word', 'sync', 'application/docx', 'doc.docx', 'ready')")
        connection.execute("INSERT INTO tbl_export_jobs (id, report_instance_id, user_id, current_format, status, exporter_backend, request_payload_hash) VALUES ('job', 'rpt', 'external-user', 'word', 'ready', 'local', '')")
        connection.commit()

    assert apply_upgrades(database_path=db_path, upgrades_dir=BUSINESS_UPGRADES, engine=engine, metadata=TableBase.metadata) == 4
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT user_id FROM tbl_template_instances WHERE id = 'ti'").fetchone() == ("external-user",)
        assert connection.execute("SELECT user_id FROM tbl_report_instances WHERE id = 'rpt'").fetchone() == ("external-user",)
        assert connection.execute("SELECT user_id FROM tbl_export_jobs WHERE id = 'job'").fetchone() == ("external-user",)
        assert connection.execute("SELECT id FROM tbl_report_documents WHERE id = 'doc'").fetchone() == ("doc",)
        assert connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'tbl_users'").fetchone() is None


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
    apply_upgrades(database_path=db_path, upgrades_dir=BUSINESS_UPGRADES, engine=engine, metadata=TableBase.metadata)
    with sqlite3.connect(db_path) as connection:
        connection.execute("UPDATE __db_schema_version SET current_version = 999 WHERE id = 1")
        connection.commit()

    with pytest.raises(DatabaseUpgradeError, match="newer than supported"):
        apply_upgrades(
            database_path=db_path,
            upgrades_dir=BUSINESS_UPGRADES,
            engine=engine,
            metadata=TableBase.metadata,
        )


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
            metadata=TableBase.metadata,
        )


def test_upgrade_rejects_unversioned_schema_drift(tmp_path):
    db_path = tmp_path / "drift.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE tbl_report_templates (id VARCHAR PRIMARY KEY)")
        connection.commit()
    engine = _engine(db_path)

    with pytest.raises(DatabaseUpgradeError, match="schema drift"):
        apply_upgrades(database_path=db_path, upgrades_dir=BUSINESS_UPGRADES, engine=engine, metadata=TableBase.metadata)


def test_gitignore_marks_runtime_directory_as_ignored():
    gitignore_path = Path(__file__).resolve().parents[5] / ".gitignore"
    gitignore_text = gitignore_path.read_text(encoding="utf-8")

    assert ".runtime/" in gitignore_text
    assert ".test/" in gitignore_text
