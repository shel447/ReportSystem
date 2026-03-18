import os
import unittest


class FrontendChatRenderTests(unittest.TestCase):
    def test_ask_param_render_shows_template_and_date_input(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        index_path = os.path.join(base, "frontend", "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("已匹配模板", content)
        self.assertIn("widget.kind === 'date'", content)

    def test_review_params_render_supports_confirm_reset_and_edit(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        index_path = os.path.join(base, "frontend", "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("m.action.type === 'review_params'", content)
        self.assertIn("confirm_generation", content)
        self.assertIn("reset_params", content)
        self.assertIn("edit_param", content)

    def test_frontend_supports_structured_param_widgets_and_v2_schema(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        index_path = os.path.join(base, "frontend", "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("param_values", content)
        self.assertIn("multi_select", content)
        self.assertIn("single_select", content)
        self.assertIn("schema_version: v2Enabled ? 'v2.0' : ''", content)
        self.assertIn("content.datasets", content)


if __name__ == "__main__":
    unittest.main()
