import unittest

from backend.chat_flow_service import (
    apply_template_selection,
    build_ask_param_action,
    upsert_slots_from_params,
)
from backend.context_state_service import new_context_state


class ChatFlowServiceTests(unittest.TestCase):
    def test_apply_template_selection_resets_slots(self):
        state = new_context_state("s1")
        state["slots"] = {"date": {"value": "2026-01-01"}}
        state["missing"]["required"] = ["date"]
        template = {"template_id": "t1", "name": "模板", "scene": "场景"}
        updated = apply_template_selection(state, template, confidence=0.9, locked=True)
        self.assertEqual(updated["report"]["template_id"], "t1")
        self.assertEqual(updated["slots"], {})
        self.assertEqual(updated["missing"]["required"], [])

    def test_build_ask_param_action_uses_first_missing(self):
        state = new_context_state("s1")
        state["missing"]["required"] = ["date", "device"]
        params = [
            {"id": "date", "label": "日期", "required": True, "input_type": "free_text", "multi": False},
            {"id": "device", "label": "设备", "required": True, "input_type": "free_text", "multi": False},
        ]
        action = build_ask_param_action(state, params)
        self.assertEqual(action["param"]["id"], "date")
        self.assertEqual(action["progress"], {"collected": 0, "required": 2})

    def test_upsert_slots_from_params_writes_values(self):
        state = new_context_state("s1")
        params = [{"id": "date", "label": "日期"}]
        updated = upsert_slots_from_params(state, {"date": "2026-01-01"}, params, source="user", turn_index=2)
        self.assertEqual(updated["slots"]["date"]["value"], "2026-01-01")
        self.assertEqual(updated["slots"]["date"]["source"], "user")

    def test_build_ask_param_action_includes_template_name(self):
        state = new_context_state("s1")
        state["missing"]["required"] = ["date"]
        state["report"] = {"template_name": "设备巡检报告"}
        params = [
            {"id": "date", "label": "日期", "required": True, "input_type": "date", "multi": False},
        ]
        action = build_ask_param_action(state, params)
        self.assertEqual(action.get("template_name"), "设备巡检报告")


if __name__ == "__main__":
    unittest.main()
