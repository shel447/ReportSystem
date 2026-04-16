import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
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
    migrate_legacy_database_to_target_schema(DB_PATH)
    init_telecom_demo_db()


def _ensure_target_table_columns(conn: sqlite3.Connection, table_name: str, columns: dict[str, str]) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    for column_name, column_sql in columns.items():
        if column_name in existing:
            continue
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")


def migrate_legacy_database_to_target_schema(db_path: str) -> None:
    from . import models  # noqa: F401

    temp_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    try:
        Base.metadata.create_all(bind=temp_engine)
    finally:
        temp_engine.dispose()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "tbl_chat_sessions" in tables:
            _ensure_target_table_columns(conn, "tbl_chat_sessions", {"matched_template_id": "TEXT"})

        _migrate_users(conn, tables)
        _migrate_templates(conn, tables)
        _migrate_instances(conn, tables)
        _migrate_template_instances(conn, tables)
        _migrate_sessions_and_messages(conn, tables)
        _normalize_chat_timestamp_columns(conn, tables)
        _migrate_documents(conn, tables)
        _migrate_tasks(conn, tables)
        _migrate_task_executions(conn, tables)
        _migrate_system_settings(conn, tables)
        _migrate_semantic_indices(conn, tables)
        _migrate_feedbacks(conn, tables)
        conn.commit()
    finally:
        conn.close()


def _table_empty(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(f"SELECT COUNT(1) AS count FROM {table_name}").fetchone()
    return int(row["count"] or 0) == 0


def _row_value(row: sqlite3.Row, key: str, default=None):
    return row[key] if key in row.keys() else default


def _ensure_user(conn: sqlite3.Connection, user_id: str) -> None:
    if not user_id:
        return
    conn.execute(
        """
        INSERT OR IGNORE INTO tbl_users (id, display_name, status, profile_json)
        VALUES (?, ?, 'active', '{}')
        """,
        (user_id, user_id),
    )


def _load_json(value: object, *, default):
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return default


def _to_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _gen_id() -> str:
    return str(uuid.uuid4())


def _next_unique_message_id(candidate: object, used_ids: set[str]) -> str:
    message_id = str(candidate or _gen_id())
    if message_id not in used_ids:
        used_ids.add(message_id)
        return message_id
    while True:
        message_id = _gen_id()
        if message_id not in used_ids:
            used_ids.add(message_id)
            return message_id


def _normalize_datetime_text(value: object, *, default: str | None = None) -> str | None:
    if value in (None, ""):
        return default
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return str(value)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat(sep=" ", timespec="seconds")


def _normalize_requirement_payload(value: object) -> object:
    if isinstance(value, list):
        return [_normalize_requirement_payload(item) for item in value]
    if not isinstance(value, dict):
        return value

    normalized = {key: _normalize_requirement_payload(item) for key, item in value.items()}

    if "document" in normalized and "requirement" not in normalized:
        normalized["requirement"] = normalized.pop("document")
    else:
        normalized.pop("document", None)

    if "requirement_template" in normalized and "requirement" not in normalized:
        normalized["requirement"] = normalized.pop("requirement_template")
    else:
        normalized.pop("requirement_template", None)

    if "blocks" in normalized and "items" not in normalized:
        normalized["items"] = normalized.pop("blocks")
    else:
        normalized.pop("blocks", None)

    if "slots" in normalized and "items" not in normalized:
        normalized["items"] = normalized.pop("slots")
    else:
        normalized.pop("slots", None)

    if "slot_id" in normalized and "item_id" not in normalized:
        normalized["item_id"] = normalized.pop("slot_id")
    else:
        normalized.pop("slot_id", None)

    if "slot_type" in normalized and "item_type" not in normalized:
        normalized["item_type"] = normalized.pop("slot_type")
    else:
        normalized.pop("slot_type", None)

    if "slot_id" in normalized and "item_id" in normalized:
        normalized.pop("slot_id", None)
    if "slot_type" in normalized and "item_type" in normalized:
        normalized.pop("slot_type", None)

    if normalized.get("kind") == "slot":
        normalized["kind"] = "item"

    return normalized


def _migrate_users(conn: sqlite3.Connection, tables: set[str]) -> None:
    if "tbl_users" not in tables:
        return
    if "chat_sessions" in tables:
        for row in conn.execute("SELECT DISTINCT COALESCE(user_id, 'default') AS user_id FROM chat_sessions"):
            _ensure_user(conn, str(row["user_id"] or "default"))
    if "scheduled_tasks" in tables:
        for row in conn.execute("SELECT DISTINCT COALESCE(user_id, 'default') AS user_id FROM scheduled_tasks"):
            _ensure_user(conn, str(row["user_id"] or "default"))


def _migrate_templates(conn: sqlite3.Connection, tables: set[str]) -> None:
    if "report_templates" not in tables or not _table_empty(conn, "tbl_report_templates"):
        return
    rows = conn.execute("SELECT * FROM report_templates").fetchall()
    for row in rows:
        content = {
            "parameters": _normalize_requirement_payload(_load_json(_row_value(row, "parameters"), default=[])),
            "sections": _normalize_requirement_payload(_load_json(_row_value(row, "sections"), default=[])),
            "match_keywords": _load_json(_row_value(row, "match_keywords"), default=[]),
            "content_params": _load_json(_row_value(row, "content_params"), default=[]),
            "outline": _normalize_requirement_payload(_load_json(_row_value(row, "outline"), default=[])),
            "output_formats": _load_json(_row_value(row, "output_formats"), default=["md"]),
        }
        conn.execute(
            """
            INSERT INTO tbl_report_templates (
                id, name, description, report_type, scenario, template_type, scene,
                schema_version, content, created_at, updated_at, created_by, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["template_id"],
                row["name"],
                _row_value(row, "description", "") or "",
                _row_value(row, "report_type", "daily") or "daily",
                _row_value(row, "scenario", "") or "",
                _row_value(row, "template_type", "") or "",
                _row_value(row, "scene", "") or "",
                _row_value(row, "schema_version", "v2.0") or "v2.0",
                _to_json(content),
                _row_value(row, "created_at"),
                _row_value(row, "created_at"),
                _row_value(row, "created_by", "system") or "system",
                _row_value(row, "version", "1.0") or "1.0",
            ),
        )


def _build_legacy_instance_source_map(conn: sqlite3.Connection, tables: set[str]) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    if "template_instances" in tables:
        for row in conn.execute("SELECT report_instance_id, session_id FROM template_instances WHERE report_instance_id IS NOT NULL AND report_instance_id != ''"):
            source = mapping.setdefault(str(row["report_instance_id"]), {})
            if row["session_id"] and not source.get("session_id"):
                source["session_id"] = str(row["session_id"])
    return mapping


def _resolve_instance_user_id(conn: sqlite3.Connection, instance_id: str, source_map: dict[str, dict[str, str]], tables: set[str]) -> str:
    session_id = source_map.get(instance_id, {}).get("session_id")
    if session_id and "chat_sessions" in tables:
        row = conn.execute("SELECT user_id FROM chat_sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row and row["user_id"]:
            return str(row["user_id"])
    if "scheduled_tasks" in tables:
        row = conn.execute("SELECT user_id FROM scheduled_tasks WHERE source_instance_id = ? LIMIT 1", (instance_id,)).fetchone()
        if row and row["user_id"]:
            return str(row["user_id"])
    raise RuntimeError(f"Unable to resolve user_id for report instance {instance_id}")


def _migrate_instances(conn: sqlite3.Connection, tables: set[str]) -> None:
    if "report_instances" not in tables or not _table_empty(conn, "tbl_report_instances"):
        return
    source_map = _build_legacy_instance_source_map(conn, tables)
    rows = conn.execute("SELECT * FROM report_instances").fetchall()
    for row in rows:
        user_id = _resolve_instance_user_id(conn, str(row["instance_id"]), source_map, tables)
        _ensure_user(conn, user_id)
        content = {
            "input_params": _load_json(row["input_params"], default={}),
            "outline_content": _normalize_requirement_payload(_load_json(row["outline_content"], default=[])),
        }
        conn.execute(
            """
            INSERT INTO tbl_report_instances (
                id, template_id, template_version, user_id, source_session_id, source_message_id,
                status, report_time, report_time_source, schema_version, content, created_at, updated_at, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["instance_id"],
                row["template_id"],
                row["template_version"] or "1.0",
                user_id,
                source_map.get(str(row["instance_id"]), {}).get("session_id"),
                None,
                row["status"] or "draft",
                row["report_time"],
                row["report_time_source"] or "",
                "v2.0",
                _to_json(content),
                row["created_at"],
                row["updated_at"] or row["created_at"],
                row["created_by"] or "system",
            ),
        )


def _migrate_template_instances(conn: sqlite3.Connection, tables: set[str]) -> None:
    if "template_instances" not in tables or not _table_empty(conn, "tbl_template_instances"):
        return
    rows = conn.execute("SELECT * FROM template_instances").fetchall()
    for row in rows:
        content = {
            "session_id": row["session_id"] or "",
            "input_params_snapshot": _load_json(row["input_params_snapshot"], default={}),
            "outline_snapshot": _normalize_requirement_payload(_load_json(row["outline_snapshot"], default=[])),
            "warnings": _load_json(row["warnings"], default=[]),
        }
        conn.execute(
            """
            INSERT INTO tbl_template_instances (
                id, template_id, template_name, template_version, session_id, capture_stage,
                report_instance_id, schema_version, content, created_at, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["template_instance_id"],
                row["template_id"],
                row["template_name"] or "",
                row["template_version"] or "1.0",
                row["session_id"] or "",
                row["capture_stage"] or "outline_saved",
                row["report_instance_id"],
                "v2.0",
                _to_json(content),
                row["created_at"],
                row["created_by"] or "system",
            ),
        )


def _migrate_sessions_and_messages(conn: sqlite3.Connection, tables: set[str]) -> None:
    if "chat_sessions" not in tables or not _table_empty(conn, "tbl_chat_sessions"):
        return
    used_message_ids = {str(row["id"]) for row in conn.execute("SELECT id FROM tbl_chat_messages").fetchall()}
    rows = conn.execute("SELECT * FROM chat_sessions").fetchall()
    for row in rows:
        user_id = str(row["user_id"] or "default")
        _ensure_user(conn, user_id)
        conn.execute(
            """
            INSERT INTO tbl_chat_sessions (id, user_id, title, matched_template_id, fork_meta, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["session_id"],
                user_id,
                row["title"] or "",
                _row_value(row, "matched_template_id"),
                row["fork_meta"] or "{}",
                row["status"] or "active",
                _normalize_datetime_text(row["created_at"]),
                _normalize_datetime_text(row["updated_at"], default=_normalize_datetime_text(row["created_at"])),
            ),
        )
        messages = _load_json(row["messages"], default=[])
        for seq_no, item in enumerate(messages, start=1):
            payload = item if isinstance(item, dict) else {}
            conn.execute(
                """
                INSERT INTO tbl_chat_messages (
                    id, session_id, user_id, role, content, action, meta, seq_no, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _next_unique_message_id(payload.get("message_id"), used_message_ids),
                    row["session_id"],
                    user_id,
                    str(payload.get("role") or "assistant"),
                    str(payload.get("content") or ""),
                    _to_json(
                        _normalize_requirement_payload(payload.get("action"))
                        if isinstance(payload.get("action"), dict)
                        else None
                    ),
                    _to_json(_load_json(payload.get("meta"), default={})),
                    seq_no,
                    _normalize_datetime_text(payload.get("created_at"), default=_normalize_datetime_text(row["created_at"])),
                ),
            )


def _normalize_chat_timestamp_columns(conn: sqlite3.Connection, tables: set[str]) -> None:
    if "tbl_chat_sessions" in tables:
        session_rows = conn.execute("SELECT id, created_at, updated_at FROM tbl_chat_sessions").fetchall()
        for row in session_rows:
            created_at = _normalize_datetime_text(row["created_at"])
            updated_at = _normalize_datetime_text(row["updated_at"], default=created_at)
            if created_at != row["created_at"] or updated_at != row["updated_at"]:
                conn.execute(
                    "UPDATE tbl_chat_sessions SET created_at = ?, updated_at = ? WHERE id = ?",
                    (created_at, updated_at, row["id"]),
                )

    if "tbl_chat_messages" in tables:
        message_rows = conn.execute("SELECT id, created_at FROM tbl_chat_messages").fetchall()
        for row in message_rows:
            normalized = _normalize_datetime_text(row["created_at"])
            if normalized != row["created_at"]:
                conn.execute(
                    "UPDATE tbl_chat_messages SET created_at = ? WHERE id = ?",
                    (normalized, row["id"]),
                )


def _migrate_documents(conn: sqlite3.Connection, tables: set[str]) -> None:
    if "report_documents" not in tables or not _table_empty(conn, "tbl_report_documents"):
        return
    rows = conn.execute("SELECT * FROM report_documents").fetchall()
    for row in rows:
        conn.execute(
            """
            INSERT INTO tbl_report_documents (
                id, instance_id, template_id, format, file_path, file_size, version, status, created_at, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["document_id"],
                row["instance_id"],
                row["template_id"] or "",
                row["format"] or "md",
                row["file_path"] or "",
                row["file_size"] or 0,
                row["version"] or 1,
                row["status"] or "ready",
                row["created_at"],
                row["created_by"] or "system",
            ),
        )


def _migrate_tasks(conn: sqlite3.Connection, tables: set[str]) -> None:
    if "scheduled_tasks" not in tables or not _table_empty(conn, "tbl_scheduled_tasks"):
        return
    rows = conn.execute("SELECT * FROM scheduled_tasks").fetchall()
    for row in rows:
        user_id = str(row["user_id"] or "default")
        _ensure_user(conn, user_id)
        conn.execute(
            """
            INSERT INTO tbl_scheduled_tasks (
                id, user_id, name, description, source_instance_id, template_id, schedule_type,
                cron_expression, timezone, enabled, auto_generate_doc, time_param_name, time_format,
                use_schedule_time_as_report_time, created_at, updated_at, last_run_at, next_run_at,
                status, total_runs, success_runs, failed_runs
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["task_id"],
                user_id,
                row["name"],
                row["description"] or "",
                row["source_instance_id"] or "",
                row["template_id"] or "",
                row["schedule_type"] or "recurring",
                row["cron_expression"] or "",
                row["timezone"] or "Asia/Shanghai",
                row["enabled"],
                row["auto_generate_doc"],
                row["time_param_name"] or "date",
                row["time_format"] or "%Y-%m-%d",
                row["use_schedule_time_as_report_time"] or 0,
                row["created_at"],
                row["updated_at"] or row["created_at"],
                row["last_run_at"],
                row["next_run_at"],
                row["status"] or "active",
                row["total_runs"] or 0,
                row["success_runs"] or 0,
                row["failed_runs"] or 0,
            ),
        )


def _migrate_task_executions(conn: sqlite3.Connection, tables: set[str]) -> None:
    if "scheduled_task_executions" not in tables or not _table_empty(conn, "tbl_scheduled_task_executions"):
        return
    rows = conn.execute("SELECT * FROM scheduled_task_executions").fetchall()
    for row in rows:
        conn.execute(
            """
            INSERT INTO tbl_scheduled_task_executions (
                id, task_id, status, generated_instance_id, started_at, completed_at, error_message, input_params_used
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["execution_id"],
                row["task_id"],
                row["status"] or "success",
                row["generated_instance_id"],
                row["started_at"],
                row["completed_at"],
                row["error_message"],
                row["input_params_used"] or "{}",
            ),
        )


def _migrate_system_settings(conn: sqlite3.Connection, tables: set[str]) -> None:
    if "system_settings" not in tables or not _table_empty(conn, "tbl_system_settings"):
        return
    rows = conn.execute("SELECT * FROM system_settings").fetchall()
    for row in rows:
        conn.execute(
            """
            INSERT INTO tbl_system_settings (id, completion_config, embedding_config, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                row["settings_id"],
                row["completion_config"] or "{}",
                row["embedding_config"] or "{}",
                row["created_at"],
                row["updated_at"] or row["created_at"],
            ),
        )


def _migrate_semantic_indices(conn: sqlite3.Connection, tables: set[str]) -> None:
    if "template_semantic_indices" not in tables or not _table_empty(conn, "tbl_template_semantic_indices"):
        return
    rows = conn.execute("SELECT * FROM template_semantic_indices").fetchall()
    for row in rows:
        conn.execute(
            """
            INSERT INTO tbl_template_semantic_indices (
                id, semantic_text, embedding_vector, embedding_model, status, error_message, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["template_id"],
                row["semantic_text"] or "",
                row["embedding_vector"] or "[]",
                row["embedding_model"] or "",
                row["status"] or "stale",
                row["error_message"],
                row["updated_at"],
            ),
        )


def _migrate_feedbacks(conn: sqlite3.Connection, tables: set[str]) -> None:
    if "feedbacks" not in tables or not _table_empty(conn, "tbl_feedbacks"):
        return
    rows = conn.execute("SELECT * FROM feedbacks").fetchall()
    for row in rows:
        conn.execute(
            """
            INSERT INTO tbl_feedbacks (id, user_ip, submitter, content, priority, images, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["feedback_id"],
                row["user_ip"],
                row["submitter"],
                row["content"],
                row["priority"] or "medium",
                row["images"] or "[]",
                row["created_at"],
            ),
        )
