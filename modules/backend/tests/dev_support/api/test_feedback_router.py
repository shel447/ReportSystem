from __future__ import annotations

import unittest
from io import BytesIO
from zipfile import ZipFile

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.infrastructure.persistence.dev_database import DevBase, get_dev_db
from src.routers.feedback import router as feedback_router


class FeedbackRouterTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.session_local = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        DevBase.metadata.create_all(bind=self.engine)
        app = FastAPI()
        app.include_router(feedback_router, prefix="/rest/dev")

        def override_get_db():
            db = self.session_local()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_dev_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        self.engine.dispose()

    def test_feedback_crud_and_zip_export(self):
        created = self.client.post(
            "/rest/dev/feedback/",
            json={"submitter": "测试人员", "content": "请优化目录样式", "priority": "high"},
        )
        self.assertEqual(created.status_code, 200)
        feedback_id = created.json()["feedback_id"]

        listed = self.client.get("/rest/dev/feedback/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()[0]["content"], "请优化目录样式")

        exported = self.client.get("/rest/dev/feedback/export.zip")
        self.assertEqual(exported.status_code, 200)
        with ZipFile(BytesIO(exported.content)) as package:
            report = package.read("feedbacks_report.md").decode("utf-8")
        self.assertIn("请优化目录样式", report)

        deleted = self.client.delete(f"/rest/dev/feedback/{feedback_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get("/rest/dev/feedback/").json(), [])
