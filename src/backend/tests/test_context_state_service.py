import copy
import unittest

from backend.context_state_service import (
    compress_state,
    new_context_state,
    persist_state_to_history,
    restore_state_from_history,
    should_persist_state,
)


class ContextStateServiceTests(unittest.TestCase):
    def test_restore_state_from_history_returns_latest(self):
        history = [
            {
                "role": "assistant",
                "content": "",
                "meta": {
                    "type": "context_state",
                    "schema_version": "ctx.v1",
                    "state": {"flow": {"turn_index": 1}, "report": {"template_id": "t1"}},
                },
            },
            {
                "role": "assistant",
                "content": "",
                "meta": {
                    "type": "context_state",
                    "schema_version": "ctx.v1",
                    "state": {"flow": {"turn_index": 2}, "report": {"template_id": "t2"}},
                },
            },
        ]
        state = restore_state_from_history(history)
        self.assertEqual(state["report"]["template_id"], "t2")
        self.assertEqual(state["flow"]["turn_index"], 2)

    def test_should_persist_state_on_stage_change(self):
        previous = new_context_state("s1")
        previous["flow"]["stage"] = "template_matching"
        current = copy.deepcopy(previous)
        current["flow"]["stage"] = "required_collection"
        self.assertTrue(should_persist_state(previous, current, turns_since_last=1, min_turns=3))

    def test_persist_state_to_history_respects_min_turns(self):
        state = new_context_state("s1")
        state["flow"]["turn_index"] = 5
        history = [
            {
                "role": "assistant",
                "content": "",
                "meta": {
                    "type": "context_state",
                    "schema_version": "ctx.v1",
                    "state": {"flow": {"turn_index": 4}},
                },
            }
        ]
        updated = persist_state_to_history(history, state, previous_state=state, min_turns=3)
        self.assertEqual(len(updated), 1)

    def test_compress_state_trims_summary(self):
        state = new_context_state("s1")
        state["summary"]["facts"] = [f"fact-{i}" for i in range(10)]
        compress_state(state, max_facts=6)
        self.assertLessEqual(len(state["summary"]["facts"]), 6)


if __name__ == "__main__":
    unittest.main()
