import json
import os
import sqlite3
import tempfile
import unittest


class SchemaCutoverMigrationTests(unittest.TestCase):
    def test_migrates_legacy_tables_into_target_tbl_structure(self):
        from backend.infrastructure.persistence.database import migrate_legacy_database_to_target_schema

        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE report_templates (
                    template_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    report_type TEXT DEFAULT 'daily',
                    scenario TEXT DEFAULT '',
                    template_type TEXT DEFAULT '',
                    scene TEXT DEFAULT '',
                    parameters JSON DEFAULT '[]',
                    sections JSON DEFAULT '[]',
                    schema_version TEXT DEFAULT '',
                    match_keywords JSON DEFAULT '[]',
                    output_formats JSON DEFAULT '[]',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT DEFAULT 'system',
                    version TEXT DEFAULT '1.0'
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE report_instances (
                    instance_id TEXT PRIMARY KEY,
                    template_id TEXT NOT NULL,
                    template_version TEXT DEFAULT '1.0',
                    status TEXT DEFAULT 'draft',
                    input_params JSON DEFAULT '{}',
                    outline_content JSON DEFAULT '[]',
                    report_time TEXT,
                    report_time_source TEXT DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT DEFAULT 'system'
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE template_instances (
                    template_instance_id TEXT PRIMARY KEY,
                    template_id TEXT NOT NULL,
                    template_name TEXT DEFAULT '',
                    template_version TEXT DEFAULT '1.0',
                    session_id TEXT DEFAULT '',
                    capture_stage TEXT DEFAULT 'outline_saved',
                    input_params_snapshot JSON DEFAULT '{}',
                    outline_snapshot JSON DEFAULT '[]',
                    warnings JSON DEFAULT '[]',
                    report_instance_id TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT DEFAULT 'system'
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT DEFAULT 'default',
                    title TEXT DEFAULT '',
                    messages JSON DEFAULT '[]',
                    fork_meta JSON DEFAULT '{}',
                    matched_template_id TEXT,
                    instance_id TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE system_settings (
                    settings_id TEXT PRIMARY KEY,
                    completion_config JSON DEFAULT '{}',
                    embedding_config JSON DEFAULT '{}',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE scheduled_tasks (
                    task_id TEXT PRIMARY KEY,
                    user_id TEXT DEFAULT 'default',
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    source_instance_id TEXT DEFAULT '',
                    template_id TEXT DEFAULT '',
                    schedule_type TEXT DEFAULT 'recurring',
                    cron_expression TEXT DEFAULT '',
                    timezone TEXT DEFAULT 'Asia/Shanghai',
                    enabled INTEGER DEFAULT 1,
                    auto_generate_doc INTEGER DEFAULT 1,
                    time_param_name TEXT DEFAULT 'date',
                    time_format TEXT DEFAULT '%Y-%m-%d',
                    use_schedule_time_as_report_time INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_run_at TEXT,
                    next_run_at TEXT,
                    status TEXT DEFAULT 'active',
                    total_runs INTEGER DEFAULT 0,
                    success_runs INTEGER DEFAULT 0,
                    failed_runs INTEGER DEFAULT 0
                )
                """
            )
            cursor.execute(
                """
                INSERT INTO report_templates (
                    template_id, name, description, report_type, scenario, template_type, scene,
                    parameters, sections, schema_version, match_keywords, output_formats, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "tpl-1",
                    "设备巡检日报",
                    "每日设备巡检报告",
                    "daily",
                    "总部",
                    "inspection",
                    "总部",
                    json.dumps([{"id": "scene", "label": "场景"}], ensure_ascii=False),
                    json.dumps(
                        [
                            {
                                "title": "总览",
                                "outline": {
                                    "document": "分析 {@metric}",
                                    "blocks": [{"id": "metric", "type": "indicator", "hint": "指标"}],
                                },
                            }
                        ],
                        ensure_ascii=False,
                    ),
                    "v2.0",
                    json.dumps(["巡检"], ensure_ascii=False),
                    json.dumps(["md"], ensure_ascii=False),
                    "1.0",
                ),
            )
            cursor.execute(
                """
                INSERT INTO report_instances (
                    instance_id, template_id, template_version, status, input_params, outline_content, report_time_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "inst-1",
                    "tpl-1",
                    "1.0",
                    "generated",
                    json.dumps({"scene": "总部"}, ensure_ascii=False),
                    json.dumps(
                        [
                            {
                                "title": "总览",
                                "requirement_instance": {
                                    "requirement_template": "分析 {@metric}",
                                    "segments": [{"kind": "slot", "slot_id": "metric", "value": "温度"}],
                                    "slots": [{"id": "metric", "type": "indicator", "value": "温度"}],
                                },
                                "execution_bindings": [{"slot_id": "metric", "targets": ["presentation.template"]}],
                            }
                        ],
                        ensure_ascii=False,
                    ),
                    "scheduled_execution",
                ),
            )
            cursor.execute(
                """
                INSERT INTO template_instances (
                    template_instance_id, template_id, template_name, session_id, capture_stage,
                    input_params_snapshot, outline_snapshot, warnings, report_instance_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "baseline-1",
                    "tpl-1",
                    "设备巡检日报",
                    "sess-1",
                    "generation_baseline",
                    json.dumps({"scene": "总部"}, ensure_ascii=False),
                    json.dumps(
                        [
                            {
                                "title": "总览",
                                "requirement_instance": {
                                    "requirement_template": "分析 {@metric}",
                                    "segments": [{"kind": "slot", "slot_id": "metric", "value": "温度"}],
                                    "slots": [{"id": "metric", "type": "indicator", "value": "温度"}],
                                },
                            }
                        ],
                        ensure_ascii=False,
                    ),
                    json.dumps([], ensure_ascii=False),
                    "inst-1",
                ),
            )
            cursor.execute(
                """
                INSERT INTO chat_sessions (
                    session_id, user_id, title, messages, fork_meta, matched_template_id, instance_id, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "sess-1",
                    "default",
                    "设备巡检",
                    json.dumps(
                        [
                            {"message_id": "m-1", "role": "user", "content": "制作巡检报告"},
                            {"message_id": "m-2", "role": "assistant", "content": "好的"},
                            {"role": "assistant", "content": "", "meta": {"type": "context_state", "state": {"x": 1}}},
                        ],
                        ensure_ascii=False,
                    ),
                    json.dumps({}, ensure_ascii=False),
                    "tpl-1",
                    "inst-1",
                    "active",
                ),
            )
            cursor.execute(
                """
                INSERT INTO system_settings (settings_id, completion_config, embedding_config)
                VALUES (?, ?, ?)
                """,
                ("global", json.dumps({"model": "x"}), json.dumps({"model": "e"})),
            )
            cursor.execute(
                """
                INSERT INTO scheduled_tasks (
                    task_id, user_id, name, source_instance_id, template_id, cron_expression, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("task-1", "default", "每日巡检", "inst-1", "tpl-1", "0 8 * * *", "active"),
            )
            conn.commit()
            conn.close()

            migrate_legacy_database_to_target_schema(db_path)

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            tables = {row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertTrue({"tbl_users", "tbl_chat_sessions", "tbl_chat_messages", "tbl_report_templates", "tbl_report_instances", "tbl_template_instances", "tbl_system_settings", "tbl_scheduled_tasks"}.issubset(tables))

            user_row = cursor.execute("SELECT id FROM tbl_users").fetchone()
            self.assertEqual(user_row[0], "default")

            template_row = cursor.execute("SELECT id, schema_version, content FROM tbl_report_templates WHERE id='tpl-1'").fetchone()
            self.assertEqual(template_row[0], "tpl-1")
            self.assertEqual(template_row[1], "v2.0")
            template_content = json.loads(template_row[2])
            self.assertEqual(template_content["parameters"][0]["id"], "scene")
            self.assertEqual(template_content["sections"][0]["title"], "总览")
            self.assertEqual(template_content["sections"][0]["outline"]["requirement"], "分析 {@metric}")
            self.assertEqual(template_content["sections"][0]["outline"]["items"][0]["id"], "metric")

            instance_row = cursor.execute(
                "SELECT id, user_id, source_session_id, source_message_id, schema_version, content FROM tbl_report_instances WHERE id='inst-1'"
            ).fetchone()
            self.assertEqual(instance_row[0], "inst-1")
            self.assertEqual(instance_row[1], "default")
            self.assertEqual(instance_row[2], "sess-1")
            self.assertIsNone(instance_row[3])
            instance_content = json.loads(instance_row[5])
            self.assertEqual(instance_content["input_params"]["scene"], "总部")
            self.assertEqual(instance_content["outline_content"][0]["requirement_instance"]["requirement"], "分析 {@metric}")
            self.assertEqual(instance_content["outline_content"][0]["requirement_instance"]["segments"][0]["kind"], "item")
            self.assertEqual(instance_content["outline_content"][0]["requirement_instance"]["items"][0]["id"], "metric")
            self.assertEqual(instance_content["outline_content"][0]["execution_bindings"][0]["item_id"], "metric")

            baseline_row = cursor.execute(
                "SELECT id, report_instance_id, schema_version, content FROM tbl_template_instances WHERE id='baseline-1'"
            ).fetchone()
            self.assertEqual(baseline_row[1], "inst-1")
            baseline_content = json.loads(baseline_row[3])
            self.assertEqual(baseline_content["outline_snapshot"][0]["requirement_instance"]["requirement"], "分析 {@metric}")
            self.assertEqual(baseline_content["outline_snapshot"][0]["requirement_instance"]["items"][0]["id"], "metric")
            baseline_content = json.loads(baseline_row[3])
            self.assertEqual(baseline_content["session_id"], "sess-1")

            messages = cursor.execute(
                "SELECT id, session_id, seq_no, role, content FROM tbl_chat_messages WHERE session_id='sess-1' ORDER BY seq_no"
            ).fetchall()
            self.assertEqual([item[0] for item in messages[:2]], ["m-1", "m-2"])
            self.assertEqual([item[2] for item in messages], [1, 2, 3])
            self.assertEqual(messages[0][4], "制作巡检报告")
        finally:
            if conn is not None:
                conn.close()
            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == "__main__":
    unittest.main()
