import unittest
from types import SimpleNamespace

from backend.routers.template_instances import list_template_instances


class TemplateInstancesRouterTests(unittest.TestCase):
    def test_list_template_instances_returns_reverse_chronological_summaries(self):
        newer = SimpleNamespace(
            template_instance_id="ti-2",
            template_id="tpl-1",
            template_name="设备巡检报告",
            session_id="sess-2",
            capture_stage="outline_confirmed",
            report_instance_id="inst-9",
            input_params_snapshot={"scene": "总部", "devices": ["A001"]},
            outline_snapshot=[
                {"display_text": "执行摘要：巡检结论", "children": []},
                {"display_text": "设备 A001：检查项", "children": []},
                {"display_text": "收尾章节：建议", "children": []},
            ],
            created_at="2026-03-19T10:00:00",
        )
        older = SimpleNamespace(
            template_instance_id="ti-1",
            template_id="tpl-1",
            template_name="设备巡检报告",
            session_id="sess-1",
            capture_stage="outline_saved",
            report_instance_id=None,
            input_params_snapshot={"scene": "总部"},
            outline_snapshot=[{"display_text": "总部概述：巡检范围", "children": []}],
            created_at="2026-03-19T09:00:00",
        )

        class FakeQuery:
            def order_by(self, *_args, **_kwargs):
                return self

            def all(self):
                return [newer, older]

        class FakeDb:
            def query(self, _model):
                return FakeQuery()

        payload = list_template_instances(db=FakeDb())

        self.assertEqual(payload[0]["template_instance_id"], "ti-2")
        self.assertEqual(payload[0]["template_name"], "设备巡检报告")
        self.assertEqual(payload[0]["capture_stage"], "outline_confirmed")
        self.assertEqual(payload[0]["report_instance_id"], "inst-9")
        self.assertEqual(payload[0]["param_count"], 2)
        self.assertEqual(payload[0]["outline_node_count"], 3)
        self.assertEqual(
            payload[0]["outline_preview"],
            ["执行摘要：巡检结论", "设备 A001：检查项", "收尾章节：建议"],
        )
        self.assertEqual(payload[1]["capture_stage"], "outline_saved")


if __name__ == "__main__":
    unittest.main()
