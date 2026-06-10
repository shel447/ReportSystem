import zipfile
from io import BytesIO

from src.main import create_app
from src.routers import docs
from tests.support.tornado_client import TornadoTestClient


def test_docs_handlers_list_read_and_download(tmp_path, monkeypatch):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "README.md").write_text("# Docs", encoding="utf-8")
    monkeypatch.setattr(docs, "DOCS_DIR", docs_dir)
    with TornadoTestClient(create_app(frontend_dir=str(tmp_path))) as client:
        assert client.get("/rest/dev/docs").json()[0]["name"] == "README.md"
        assert client.get("/rest/dev/docs/README").json()["content"] == "# Docs"
        archive = zipfile.ZipFile(BytesIO(client.get("/rest/dev/docs/download.zip").content))
        assert "README.md" in archive.namelist()


def test_docs_handler_rejects_directory_escape(tmp_path, monkeypatch):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    monkeypatch.setattr(docs, "DOCS_DIR", docs_dir)
    with TornadoTestClient(create_app(frontend_dir=str(tmp_path))) as client:
        assert client.get("/rest/dev/docs/%2E%2E/secret.md").status_code == 404
