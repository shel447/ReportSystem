import unittest
from types import SimpleNamespace

from backend.contexts.report_runtime.domain.services import is_v2_template


class TemplateVersionTests(unittest.TestCase):
    def test_is_v2_template_true_when_schema_version(self):
        template = SimpleNamespace(schema_version="v2", sections=None)
        self.assertTrue(is_v2_template(template))

    def test_is_v2_template_true_when_sections_present(self):
        template = SimpleNamespace(schema_version=None, sections=[{"title": "x"}])
        self.assertTrue(is_v2_template(template))

    def test_is_v2_template_false_when_no_sections(self):
        template = SimpleNamespace(schema_version=None, sections=None)
        self.assertFalse(is_v2_template(template))


if __name__ == "__main__":
    unittest.main()
