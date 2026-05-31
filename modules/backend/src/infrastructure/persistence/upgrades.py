"""Apply versioned SQLite upgrades and verify the resulting schema."""

from __future__ import annotations

from pathlib import Path
import re
import sqlite3

from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.sql.schema import MetaData


VERSION_TABLE = "__db_schema_version"
_UPGRADE_PATTERN = re.compile(r"^V(?P<version>\d{3})__(?P<name>.+)\.sql$")


class DatabaseUpgradeError(RuntimeError):
    """Raised when a database cannot be upgraded to the expected schema."""


def apply_upgrades(*, database_path: Path, upgrades_dir: Path, engine: Engine, metadata: MetaData) -> int:
    """Upgrade a SQLite database and validate the ORM-facing schema."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    scripts = _collect_upgrade_scripts(upgrades_dir)
    metadata_script = scripts.pop(0, None)
    if metadata_script is None:
        raise DatabaseUpgradeError(f"Missing V000 database metadata upgrade in {upgrades_dir}")

    with sqlite3.connect(database_path) as connection:
        connection.executescript(metadata_script.read_text(encoding="utf-8"))
        current_version = _read_current_version(connection)
        latest_version = max(scripts, default=0)
        if current_version > latest_version:
            raise DatabaseUpgradeError(
                f"Database version {current_version} is newer than supported version {latest_version}: {database_path}"
            )
        for version in range(current_version + 1, latest_version + 1):
            script = scripts[version]
            sql = script.read_text(encoding="utf-8")
            connection.executescript(
                "BEGIN;\n"
                f"{sql}\n"
                f"UPDATE {VERSION_TABLE} SET current_version = {version}, updated_at = CURRENT_TIMESTAMP WHERE id = 1;\n"
                "COMMIT;\n"
            )

    _validate_schema(engine=engine, metadata=metadata, database_path=database_path)
    return latest_version


def _collect_upgrade_scripts(upgrades_dir: Path) -> dict[int, Path]:
    scripts: dict[int, Path] = {}
    for path in sorted(upgrades_dir.glob("V*.sql")):
        match = _UPGRADE_PATTERN.match(path.name)
        if match is None:
            raise DatabaseUpgradeError(f"Invalid database upgrade filename: {path.name}")
        version = int(match.group("version"))
        if version in scripts:
            raise DatabaseUpgradeError(f"Duplicate database upgrade version V{version:03d} in {upgrades_dir}")
        scripts[version] = path
    if not scripts:
        raise DatabaseUpgradeError(f"No database upgrade scripts found in {upgrades_dir}")
    expected = list(range(0, max(scripts) + 1))
    if sorted(scripts) != expected:
        raise DatabaseUpgradeError(f"Database upgrade versions must be continuous from V000 in {upgrades_dir}")
    return scripts


def _read_current_version(connection: sqlite3.Connection) -> int:
    row = connection.execute(f"SELECT current_version FROM {VERSION_TABLE} WHERE id = 1").fetchone()
    if row is None:
        raise DatabaseUpgradeError(f"{VERSION_TABLE} must contain the singleton row id = 1")
    return int(row[0])


def _validate_schema(*, engine: Engine, metadata: MetaData, database_path: Path) -> None:
    inspector = inspect(engine)
    available_tables = set(inspector.get_table_names())
    required_tables = set(metadata.tables)
    missing_tables = sorted(required_tables - available_tables)
    if missing_tables:
        raise DatabaseUpgradeError(
            f"Database schema drift detected in {database_path}; missing tables: {', '.join(missing_tables)}. "
            "Delete .runtime/ and restart to rebuild the local database."
        )
    for table_name, table in metadata.tables.items():
        available_columns = {item["name"] for item in inspector.get_columns(table_name)}
        missing_columns = sorted(set(table.columns.keys()) - available_columns)
        if missing_columns:
            raise DatabaseUpgradeError(
                f"Database schema drift detected in {database_path}; {table_name} is missing columns: "
                f"{', '.join(missing_columns)}. Delete .runtime/ and restart to rebuild the local database."
            )
