import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.infrastructure.persistence.database import Base, get_db
from backend.routers.system_settings import router as system_settings_router


class SystemSettingsRouterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.temp_dir.name, "settings-test.db")
        self.engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        self.session_local = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        app = FastAPI()
        app.include_router(system_settings_router, prefix="/rest/dev")

        def override_get_db():
            db = self.session_local()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_get_system_settings_returns_default_payload(self):
        response = self.client.get("/rest/dev/system-settings")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("completion", payload)
        self.assertIn("embedding", payload)
        self.assertFalse(payload["is_ready"])
        self.assertIn("index_status", payload)

    def test_put_system_settings_persists_configs(self):
        response = self.client.put(
            "/rest/dev/system-settings",
            json={
                "completion": {
                    "base_url": "https://example.com/v1",
                    "model": "gpt-5.4",
                    "api_key": "secret-completion",
                    "temperature": 0.1,
                    "timeout_sec": 30,
                },
                "embedding": {
                    "model": "text-embedding-3-large",
                    "use_completion_auth": True,
                    "timeout_sec": 20,
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["completion"]["configured"])
        self.assertTrue(payload["embedding"]["configured"])
        self.assertTrue(payload["is_ready"])


if __name__ == "__main__":
    unittest.main()
