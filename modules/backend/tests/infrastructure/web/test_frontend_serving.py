import os
import tempfile
import unittest
from unittest.mock import patch

from tests.support.tornado_client import TornadoTestClient as TestClient
from src.main import create_app
from src.shared.kernel.errors import ErrorCode


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

    def test_removed_public_resource_paths_return_404(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = os.path.join(temp_dir, "index.html")
            with open(index_path, "w", encoding="utf-8") as f:
                f.write("<html><body>spa-entry</body></html>")

            client = TestClient(create_app(frontend_dir=temp_dir))

            for path in (
                "/rest/chatbi/v1/instances",
                "/rest/chatbi/v1/scheduled-tasks",
                "/rest/chatbi/v1/documents",
            ):
                response = client.get(path, headers={"X-User-Id": "default"})
                self.assertEqual(response.status_code, 404, path)
                self.assertNotIn("spa-entry", response.text)

    def test_chatbi_business_routes_require_non_blank_user_header(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = os.path.join(temp_dir, "index.html")
            with open(index_path, "w", encoding="utf-8") as f:
                f.write("<html><body>spa-entry</body></html>")

            client = TestClient(create_app(frontend_dir=temp_dir))

            requests = (
                lambda: client.get("/rest/chatbi/v1/templates"),
                lambda: client.get("/rest/chatbi/v1/chat"),
                lambda: client.get("/rest/chatbi/v1/reports/rpt_missing"),
            )
            for send in requests:
                response = send()
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json()["errorCode"], ErrorCode.BASE_AUTH_REQUIRED)

            blank = client.get("/rest/chatbi/v1/templates", headers={"X-User-Id": ""})
            self.assertEqual(blank.status_code, 401)
            self.assertEqual(blank.json()["errorCode"], ErrorCode.BASE_AUTH_REQUIRED)

    def test_parameter_options_resolver_is_not_a_public_business_route(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = os.path.join(temp_dir, "index.html")
            with open(index_path, "w", encoding="utf-8") as f:
                f.write("<html><body>spa-entry</body></html>")

            client = TestClient(create_app(frontend_dir=temp_dir))

            get_response = client.get(
                "/rest/chatbi/v1/parameter-options/resolve",
                headers={"X-User-Id": "default"},
            )
            post_response = client.post(
                "/rest/chatbi/v1/parameter-options/resolve",
                headers={"X-User-Id": "default"},
                json={},
            )

            self.assertEqual(get_response.status_code, 404)
            self.assertIn(post_response.status_code, {404, 405})

    def test_dev_routes_do_not_require_user_header(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = os.path.join(temp_dir, "index.html")
            with open(index_path, "w", encoding="utf-8") as f:
                f.write("<html><body>spa-entry</body></html>")

            client = TestClient(create_app(frontend_dir=temp_dir))

            response = client.get("/rest/dev/docs")

            self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
