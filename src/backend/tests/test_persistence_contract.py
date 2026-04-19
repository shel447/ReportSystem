from pathlib import Path

from backend.infrastructure.persistence.database import Base


def test_schema_init_sql_covers_current_orm_tables():
    schema_path = Path(__file__).resolve().parents[1] / "infrastructure" / "persistence" / "schema_init.sql"
    sql_text = schema_path.read_text(encoding="utf-8")

    for table_name in Base.metadata.tables.keys():
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in sql_text


def test_gitignore_marks_runtime_database_as_ignored():
    gitignore_path = Path(__file__).resolve().parents[3] / ".gitignore"
    gitignore_text = gitignore_path.read_text(encoding="utf-8")

    assert "src/backend/report_system.db" in gitignore_text
