import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from backend.main import create_app


class FrontendServingTests(unittest.TestCase):
    def test_root_serves_dist_index_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = os.path.join(temp_dir, "index.html")
            with open(index_path, "w", encoding="utf-8") as f:
                f.write("<html><body>frontend-dist</body></html>")

            client = TestClient(create_app(frontend_dir=temp_dir))

            response = client.get("/")

            self.assertEqual(response.status_code, 200)
            self.assertIn("frontend-dist", response.text)

    def test_spa_route_serves_same_index_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = os.path.join(temp_dir, "index.html")
            with open(index_path, "w", encoding="utf-8") as f:
                f.write("<html><body>spa-entry</body></html>")

            client = TestClient(create_app(frontend_dir=temp_dir))

            response = client.get("/chat")

            self.assertEqual(response.status_code, 200)
            self.assertIn("spa-entry", response.text)

    def test_rest_and_legacy_api_paths_do_not_fall_back_to_spa(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = os.path.join(temp_dir, "index.html")
            with open(index_path, "w", encoding="utf-8") as f:
                f.write("<html><body>spa-entry</body></html>")

            client = TestClient(create_app(frontend_dir=temp_dir))

            rest_response = client.get("/rest/chatbi/v1/unknown")
            legacy_response = client.get("/api/unknown")

            self.assertEqual(rest_response.status_code, 404)
            self.assertNotIn("spa-entry", rest_response.text)
            self.assertEqual(legacy_response.status_code, 404)
            self.assertNotIn("spa-entry", legacy_response.text)


if __name__ == "__main__":
    unittest.main()
