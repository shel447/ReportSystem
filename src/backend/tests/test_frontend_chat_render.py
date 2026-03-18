import os
import unittest


class FrontendChatRenderTests(unittest.TestCase):
    def test_ask_param_render_shows_template_and_date_input(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        panel_path = os.path.join(base, "frontend", "src", "features", "chat-report-flow", "components", "ChatActionPanel.tsx")
        with open(panel_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("已匹配模板", content)
        self.assertIn('action.widget.kind === "date"', content)

    def test_review_params_render_supports_confirm_reset_and_edit(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        panel_path = os.path.join(base, "frontend", "src", "features", "chat-report-flow", "components", "ChatActionPanel.tsx")
        with open(panel_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('action.type === "review_params"', content)
        self.assertIn("confirm_generation", content)
        self.assertIn("reset_params", content)
        self.assertIn("edit_param", content)

    def test_frontend_supports_structured_param_widgets_and_v2_schema(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        chat_page_path = os.path.join(base, "frontend", "src", "pages", "ChatPage.tsx")
        template_catalog_path = os.path.join(base, "frontend", "src", "pages", "TemplatesPage.tsx")
        template_detail_path = os.path.join(base, "frontend", "src", "pages", "TemplateDetailPage.tsx")
        panel_path = os.path.join(base, "frontend", "src", "features", "chat-report-flow", "components", "ChatActionPanel.tsx")
        with open(chat_page_path, "r", encoding="utf-8") as f:
            chat_content = f.read()
        with open(template_catalog_path, "r", encoding="utf-8") as f:
            template_catalog_content = f.read()
        with open(template_detail_path, "r", encoding="utf-8") as f:
            template_detail_content = f.read()
        with open(panel_path, "r", encoding="utf-8") as f:
            panel_content = f.read()
        self.assertIn("param_values", chat_content)
        self.assertIn("multi_select", panel_content)
        self.assertIn("single_select", panel_content)
        self.assertIn("/templates/new", template_catalog_content)
        self.assertIn("schemaVersion", template_detail_content)
        self.assertIn("sectionsText", template_detail_content)

    def test_chat_styles_keep_message_stream_balanced(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        pages_css_path = os.path.join(base, "frontend", "src", "styles", "pages.css")
        with open(pages_css_path, "r", encoding="utf-8") as f:
            styles = f.read()
        self.assertIn(".message-list {\n  display: flex;", styles)
        self.assertIn("flex-direction: column;", styles)
        self.assertIn("min-height: 320px", styles)
        self.assertIn("min-height: 64px", styles)


if __name__ == "__main__":
    unittest.main()
