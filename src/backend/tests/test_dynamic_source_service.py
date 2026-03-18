import unittest

from backend.dynamic_source_service import get_dynamic_options


class DynamicSourceServiceTests(unittest.TestCase):
    def test_unknown_source_returns_empty(self):
        self.assertEqual(get_dynamic_options("api:/unknown"), [])

    def test_known_source_returns_list(self):
        result = get_dynamic_options("api:/devices/list")
        self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()
