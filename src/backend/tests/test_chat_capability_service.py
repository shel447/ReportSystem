import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.chat_capability_service import handle_fault_diagnosis_turn, handle_smart_query_turn
from backend.query_engine import QueryRunResult


class ChatCapabilityServiceTests(unittest.TestCase):
    def test_handle_smart_query_turn_returns_structured_result_and_debug_context(self):
        fake_result = QueryRunResult(
            success=True,
            model="query-model",
            compiled_sql="SELECT region_name, alarm_count FROM top_alarm_regions",
            sample_rows=[
                {"region_name": "华东", "alarm_count": 28},
                {"region_name": "华南", "alarm_count": 19},
            ],
            row_count=2,
            debug={
                "strategy": "ibis_planner",
                "query_spec": {
                    "intent": "统计昨日各区域告警量",
                    "tables": ["fact_alarm_event"],
                    "dimensions": ["region_name"],
                    "measures": ["alarm_count"],
                    "filters": [{"field": "event_date", "op": "=", "value": "昨天"}],
                    "warnings": ["时间范围按昨天理解"],
                },
                "schema_candidates": [{"table": "fact_alarm_event", "score": 6}],
                "compiled_sql": "SELECT region_name, alarm_count FROM top_alarm_regions",
                "error_stage": "",
                "error_message": "",
            },
        )

        with patch("backend.chat_capability_service.build_completion_provider_config", return_value=SimpleNamespace(temperature=0.2, model="query-model")), \
             patch("backend.chat_capability_service.run_query", return_value=fake_result):
            reply, action, task_update = handle_smart_query_turn(
                db=object(),
                gateway=SimpleNamespace(),
                message="我想知道昨天各区域告警量",
                state={},
            )

        self.assertIsNone(action)
        self.assertEqual(task_update["stage"], "answered")
        self.assertIn("已完成智能问数", reply)
        self.assertIn("统计昨日各区域告警量", reply)
        self.assertIn("华东", reply)
        self.assertIn("时间范围按昨天理解", reply)
        self.assertEqual(task_update["context_payload"]["compiled_sql"], "SELECT region_name, alarm_count FROM top_alarm_regions")
        self.assertEqual(task_update["context_payload"]["query_debug"]["strategy"], "ibis_planner")

    def test_handle_smart_query_turn_returns_clarification_on_query_failure(self):
        fake_result = QueryRunResult(
            success=False,
            model="query-model",
            compiled_sql="",
            sample_rows=[],
            row_count=0,
            debug={
                "strategy": "ibis_planner",
                "query_spec": {
                    "intent": "查询站点告警情况",
                    "warnings": ["缺少明确时间范围"],
                },
                "schema_candidates": [{"table": "fact_alarm_event", "score": 6}],
                "compiled_sql": "",
                "error_stage": "planning",
                "error_message": "缺少明确时间范围",
            },
        )

        with patch("backend.chat_capability_service.build_completion_provider_config", return_value=SimpleNamespace(temperature=0.2, model="query-model")), \
             patch("backend.chat_capability_service.run_query", return_value=fake_result):
            reply, action, task_update = handle_smart_query_turn(
                db=object(),
                gateway=SimpleNamespace(),
                message="帮我看下站点告警情况",
                state={},
            )

        self.assertIsNone(action)
        self.assertEqual(task_update["stage"], "clarifying")
        self.assertIn("没有成功执行", reply)
        self.assertIn("缺少明确时间范围", reply)
        self.assertIn("clarification_question", task_update["context_payload"])

    def test_handle_fault_diagnosis_turn_returns_structured_summary(self):
        diagnosis_json = """
        {
          "symptom_summary": "1号站点昨晚出现疑似掉站。",
          "judgment": "更像是站点退服或回传中断。",
          "possible_causes": ["站点主设备离线", "回传链路中断"],
          "next_steps": ["检查退服与电源告警", "核查传输链路状态"],
          "missing_info": [],
          "risk_level": "high"
        }
        """
        with patch("backend.chat_capability_service.build_completion_provider_config", return_value=SimpleNamespace(temperature=0.4, model="diag-model")):
            gateway = SimpleNamespace(chat_completion=lambda *args, **kwargs: {"content": diagnosis_json, "model": "diag-model"})
            reply, action, task_update = handle_fault_diagnosis_turn(
                db=object(),
                gateway=gateway,
                message="帮我分析 1 号站点昨晚是不是掉站了",
                state={},
            )

        self.assertIsNone(action)
        self.assertEqual(task_update["stage"], "answered")
        self.assertIn("已进入智能故障分析", reply)
        self.assertIn("站点主设备离线", reply)
        self.assertEqual(task_update["context_payload"]["risk_level"], "high")
        self.assertEqual(task_update["context_payload"]["possible_causes"][1], "回传链路中断")

    def test_handle_fault_diagnosis_turn_returns_clarification_when_missing_info(self):
        diagnosis_json = """
        {
          "symptom_summary": "站点出现异常。",
          "judgment": "当前信息不足，只能给出通用排查方向。",
          "possible_causes": ["站点退服", "链路波动"],
          "next_steps": ["补充站点对象", "补充发生时间"],
          "missing_info": ["具体站点", "发生时间"],
          "risk_level": "medium"
        }
        """
        with patch("backend.chat_capability_service.build_completion_provider_config", return_value=SimpleNamespace(temperature=0.4, model="diag-model")):
            gateway = SimpleNamespace(chat_completion=lambda *args, **kwargs: {"content": diagnosis_json, "model": "diag-model"})
            reply, action, task_update = handle_fault_diagnosis_turn(
                db=object(),
                gateway=gateway,
                message="帮我看下是不是出问题了",
                state={},
            )

        self.assertIsNone(action)
        self.assertEqual(task_update["stage"], "clarifying")
        self.assertIn("建议补充", reply)
        self.assertIn("具体站点", reply)
        self.assertEqual(task_update["context_payload"]["missing_info"], ["具体站点", "发生时间"])


if __name__ == "__main__":
    unittest.main()
