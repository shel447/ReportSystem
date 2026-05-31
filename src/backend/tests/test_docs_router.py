import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.routers import docs


class DocsRouterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.docs_dir = Path(self.temp_dir.name)
        (self.docs_dir / "implementation" / "contracts" / "schemas").mkdir(parents=True)
        (self.docs_dir / "specs").mkdir()
        (self.docs_dir / "README.md").write_text("# Docs\n", encoding="utf-8")
        (self.docs_dir / "specs" / "README.md").write_text("# Specs\n", encoding="utf-8")
        (self.docs_dir / "implementation" / "contracts" / "schemas" / "sample.json").write_text(
            '{"ok": true}\n',
            encoding="utf-8",
        )
        (self.docs_dir / "ignored.txt").write_text("ignore me\n", encoding="utf-8")

        self.docs_dir_patch = patch.object(docs, "DOCS_DIR", self.docs_dir)
        self.docs_dir_patch.start()

        app = FastAPI()
        app.include_router(docs.router, prefix="/rest/dev")
        self.client = TestClient(app)

    def tearDown(self):
        self.docs_dir_patch.stop()
        self.temp_dir.cleanup()

    def test_list_docs_returns_recursive_markdown_and_json_assets(self):
        response = self.client.get("/rest/dev/docs")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["name"] for item in response.json()],
            ["README.md", "implementation/contracts/schemas/sample.json", "specs/README.md"],
        )
        self.assertEqual(response.json()[0]["type"], "markdown")
        self.assertEqual(response.json()[1]["type"], "json")

    def test_get_doc_supports_nested_markdown_without_suffix_and_json(self):
        markdown = self.client.get("/rest/dev/docs/specs/README")
        schema = self.client.get("/rest/dev/docs/implementation/contracts/schemas/sample.json")

        self.assertEqual(markdown.status_code, 200)
        self.assertEqual(markdown.json()["name"], "specs/README.md")
        self.assertEqual(markdown.json()["content"], "# Specs\n")
        self.assertEqual(schema.status_code, 200)
        self.assertEqual(schema.json()["type"], "json")

    def test_download_docs_zip_keeps_nested_paths_and_filters_other_files(self):
        response = self.client.get("/rest/dev/docs/download.zip")

        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertEqual(
                archive.namelist(),
                ["README.md", "implementation/contracts/schemas/sample.json", "specs/README.md"],
            )

    def test_path_escape_and_legacy_design_route_are_rejected(self):
        with self.assertRaises(HTTPException):
            docs._resolve_doc_path("../README.md")

        response = self.client.get("/rest/dev/design")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
