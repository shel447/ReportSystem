import os
import tempfile
import unittest
from unittest.mock import patch

from backend.contexts.template_catalog.application.parameter_options import ParameterOptionService
from backend.infrastructure.demo.dynamic_sources import get_dynamic_option_items, get_dynamic_options


class DynamicSourceServiceTests(unittest.TestCase):
    def test_unknown_source_returns_empty(self):
        self.assertEqual(get_dynamic_options("api:/unknown"), [])

    def test_known_source_returns_list(self):
        result = get_dynamic_options("api:/devices/list")
        self.assertIsInstance(result, list)

    def test_known_source_initializes_empty_demo_db(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            demo_db_path = os.path.join(temp_dir, "telecom_demo.db")
            open(demo_db_path, "a", encoding="utf-8").close()
            with patch("backend.infrastructure.demo.telecom.DEMO_DB_PATH", demo_db_path):
                result = get_dynamic_options("api:/devices/list")
            self.assertTrue(result)

    def test_known_source_returns_formal_trio_values(self):
        result = get_dynamic_option_items("api:/sites/list")
        self.assertTrue(result)
        self.assertIn("display", result[0])
        self.assertIn("value", result[0])
        self.assertIn("query", result[0])

    def test_parameter_option_service_resolves_demo_source_into_formal_response(self):
        payload = ParameterOptionService().resolve(
            user_id="default",
            parameter_id="scope",
            source="api:/sites/list",
            context_values={},
        )
        self.assertTrue(payload["options"])
        self.assertIn("display", payload["options"][0])
        self.assertIn("value", payload["options"][0])
        self.assertIn("query", payload["options"][0])


if __name__ == "__main__":
    unittest.main()
