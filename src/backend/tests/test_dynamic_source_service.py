import os
import tempfile
import unittest
from unittest.mock import patch

from backend.infrastructure.demo.dynamic_sources import get_dynamic_options


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


if __name__ == "__main__":
    unittest.main()
