import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.infrastructure.persistence.database import Base
from backend.infrastructure.persistence.models import ReportInstance
from backend.routers.tasks import TaskCreate, create_task, run_task_now


class FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 3, 31, 8, 0, 0, tzinfo=tz)


class TasksRouterTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
        self.db.add(
            ReportInstance(
                instance_id="inst-src",
                template_id="tpl-1",
                template_version="1.0",
                status="generated",
                input_params={"scene": "总部"},
                outline_content=[],
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_list_tasks_uses_header_user_id_instead_of_query_default(self):
        create_task(
            TaskCreate(
                name="默认用户任务",
                source_instance_id="inst-src",
                template_id="tpl-1",
                user_id="default",
            ),
            db=self.db,
            user_id="default",
        )
        create_task(
            TaskCreate(
                name="其他用户任务",
                source_instance_id="inst-src",
                template_id="tpl-1",
                user_id="other",
            ),
            db=self.db,
            user_id="other",
        )

        from backend.routers.tasks import list_tasks

        payload = list_tasks(db=self.db, user_id="default")

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["name"], "默认用户任务")

    def test_create_task_round_trips_time_mapping_fields(self):
        created = create_task(
            TaskCreate(
                name="每日巡检",
                description="每日自动生成",
                source_instance_id="inst-src",
                template_id="tpl-1",
                schedule_type="recurring",
                cron_expression="0 8 * * *",
                auto_generate_doc=True,
                time_param_name="report_date",
                time_format="%Y-%m-%d",
                use_schedule_time_as_report_time=True,
            ),
            db=self.db,
        )

        self.assertEqual(created["time_param_name"], "report_date")
        self.assertEqual(created["time_format"], "%Y-%m-%d")
        self.assertTrue(created["use_schedule_time_as_report_time"])

    def test_run_task_now_uses_schedule_time_for_param_and_report_time(self):
        task = create_task(
            TaskCreate(
                name="每日巡检",
                description="每日自动生成",
                source_instance_id="inst-src",
                template_id="tpl-1",
                schedule_type="recurring",
                cron_expression="0 8 * * *",
                auto_generate_doc=True,
                time_param_name="report_date",
                time_format="%Y-%m-%d %H:%M",
                use_schedule_time_as_report_time=True,
            ),
            db=self.db,
        )
        captured = {}

        class FakeSchedulingService:
            def run_task_now(self, _task_id, user_id=None):
                captured.update(
                    {
                        "override_params": {"report_date": "2026-03-31 08:00"},
                        "report_time": datetime(2026, 3, 31, 8, 0, 0),
                        "report_time_source": "scheduled_execution",
                        "user_id": user_id,
                    }
                )
                return {
                    "instance_id": "inst-generated",
                    "document_id": "doc-1",
                }

        with patch("backend.routers.tasks.build_scheduling_service", return_value=FakeSchedulingService()):
            payload = run_task_now(task["task_id"], db=self.db)

        self.assertEqual(payload["instance_id"], "inst-generated")
        self.assertEqual(captured["override_params"]["report_date"], "2026-03-31 08:00")
        self.assertEqual(captured["report_time"], datetime(2026, 3, 31, 8, 0, 0))
        self.assertEqual(captured["report_time_source"], "scheduled_execution")
        self.assertEqual(captured["user_id"], "default")


if __name__ == "__main__":
    unittest.main()
