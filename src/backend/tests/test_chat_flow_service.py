import unittest

from backend.contexts.conversation.infrastructure.flow import (
    apply_template_selection,
    build_ask_param_action,
    build_review_outline_action,
    build_review_params_action,
    reset_slots,
    rewind_slots_for_param,
    upsert_slots_from_params,
)
from backend.contexts.conversation.infrastructure.state import new_context_state


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

    def test_build_ask_param_action_includes_structured_widget(self):
        state = new_context_state("s1")
        state["missing"]["required"] = ["devices"]
        state["slots"] = {"devices": {"value": ["A001"], "source": "user"}}
        params = [
            {
                "id": "devices",
                "label": "设备编号",
                "required": True,
                "input_type": "dynamic",
                "multi": True,
                "options": ["A001", "A002"],
            },
        ]
        action = build_ask_param_action(state, params)
        self.assertEqual(action["widget"]["kind"], "multi_select")
        self.assertEqual(action["selected_values"], ["A001"])

    def test_build_review_params_action_returns_ordered_collected_params(self):
        state = new_context_state("s1")
        state["report"] = {"template_name": "设备巡检报告", "template_id": "t1"}
        state["slots"] = {
            "scene": {"value": "总部"},
            "devices": {"value": ["A001", "A002"]},
        }
        params = [
            {"id": "scene", "label": "场景", "required": True},
            {"id": "devices", "label": "设备", "required": True},
        ]
        action = build_review_params_action(state, params)
        self.assertEqual(action["type"], "review_params")
        self.assertEqual(action["params"][0]["id"], "scene")
        self.assertEqual(action["params"][1]["value"], ["A001", "A002"])

    def test_build_review_outline_action_returns_sanitized_outline_and_param_snapshot(self):
        state = new_context_state("s1")
        state["report"] = {
            "template_name": "设备巡检报告",
            "template_id": "t1",
            "pending_outline_review": [
                {
                    "node_id": "node-1",
                    "title": "概览",
                    "description": "说明",
                    "level": 1,
                    "children": [],
                    "section_kind": "freeform_leaf",
                    "node_kind": "freeform_leaf",
                    "display_text": "概览：说明",
                    "ai_generated": True,
                    "outline_instance": {
                        "document_template": "分析 {@metric}",
                        "rendered_document": "分析 温度",
                        "blocks": [{"id": "metric", "value": "温度"}],
                    },
                    "execution_bindings": [{"block_id": "metric", "targets": ["presentation.template"]}],
                    "content": {"presentation": {"type": "text", "template": "ok"}},
                }
            ],
            "outline_review_warnings": ["x"],
        }
        state["slots"] = {"scene": {"value": "总部"}}
        params = [{"id": "scene", "label": "场景", "required": True}]

        action = build_review_outline_action(state, params)

        self.assertEqual(action["type"], "review_outline")
        self.assertEqual(action["warnings"], ["x"])
        self.assertEqual(action["outline"][0]["node_id"], "node-1")
        self.assertNotIn("content", action["outline"][0])
        self.assertEqual(action["outline"][0]["display_text"], "概览：说明")
        self.assertEqual(action["outline"][0]["node_kind"], "freeform_leaf")
        self.assertTrue(action["outline"][0]["ai_generated"])
        self.assertEqual(action["outline"][0]["outline_instance"]["rendered_document"], "分析 温度")
        self.assertEqual(action["outline"][0]["execution_bindings"][0]["block_id"], "metric")
        self.assertEqual(action["params_snapshot"][0]["value"], "总部")

    def test_rewind_slots_for_param_clears_target_and_following_slots(self):
        state = new_context_state("s1")
        state["slots"] = {
            "scene": {"value": "总部"},
            "date": {"value": "2026-03-18"},
            "devices": {"value": ["A001"]},
        }
        params = [
            {"id": "scene", "label": "场景", "required": True},
            {"id": "date", "label": "日期", "required": True},
            {"id": "devices", "label": "设备", "required": True},
        ]
        updated = rewind_slots_for_param(state, params, "date")
        self.assertIn("scene", updated["slots"])
        self.assertNotIn("date", updated["slots"])
        self.assertNotIn("devices", updated["slots"])
        self.assertEqual(updated["missing"]["required"], ["date", "devices"])

    def test_reset_slots_clears_collection_state(self):
        state = new_context_state("s1")
        state["slots"] = {"scene": {"value": "总部"}}
        state["missing"]["required"] = ["date"]
        updated = reset_slots(state)
        self.assertEqual(updated["slots"], {})
        self.assertEqual(updated["missing"]["required"], [])


if __name__ == "__main__":
    unittest.main()
