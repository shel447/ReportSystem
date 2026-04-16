import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import create_app
from backend.infrastructure.persistence.database import Base
from backend.infrastructure.persistence.models import User


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

    def test_chatbi_request_creates_user_mirror_record(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = os.path.join(temp_dir, "index.html")
            with open(index_path, "w", encoding="utf-8") as f:
                f.write("<html><body>spa-entry</body></html>")

            db_path = os.path.join(temp_dir, "test.db")
            engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
            testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            Base.metadata.create_all(bind=engine)

            with patch("backend.main.SessionLocal", testing_session_local), patch("backend.main.init_db", lambda: None):
                client = TestClient(create_app(frontend_dir=temp_dir))

                response = client.get("/rest/chatbi/v1/unknown", headers={"X-User-Id": "middleware-user"})

                self.assertEqual(response.status_code, 404)
                with testing_session_local() as db:
                    user = db.query(User).filter(User.id == "middleware-user").first()
                    self.assertIsNotNone(user)


if __name__ == "__main__":
    unittest.main()
