from pathlib import Path
import unittest

from backend.contexts.report_runtime.infrastructure import rendering
from backend.infrastructure.demo import telecom
from backend.infrastructure.persistence import database


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class RuntimePathTests(unittest.TestCase):
    def test_primary_database_path_remains_under_backend_root(self):
        expected = BACKEND_ROOT / "report_system.db"
        self.assertEqual(expected, Path(database.DB_PATH).resolve())

    def test_demo_database_path_remains_under_backend_root(self):
        expected = BACKEND_ROOT / "telecom_demo.db"
        self.assertEqual(expected, Path(telecom.DEMO_DB_PATH).resolve())

    def test_report_runtime_default_db_path_uses_canonical_demo_database(self):
        self.assertEqual(Path(telecom.DEMO_DB_PATH).resolve(), Path(rendering.DEFAULT_DB_PATH).resolve())


if __name__ == "__main__":
    unittest.main()
