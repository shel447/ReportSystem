from pathlib import Path
from types import SimpleNamespace

from src.contexts.report.application.generation_models import DocumentView, DownloadResolution
from src.main import create_app
from src.shared.kernel.errors import ValidationError
from tests.support.tornado_client import FakeWebContainer, TornadoTestClient


def test_report_download_handler_streams_resolved_file(tmp_path):
    artifact = tmp_path / "report.md"
    artifact.write_text("# report\n", encoding="utf-8")
    document = DocumentView(id="doc_1", format="markdown", mime_type="text/markdown", file_name="report.md", download_url="", status="ready")
    report = SimpleNamespace(answer=SimpleNamespace(documents=[document]))
    service = SimpleNamespace(
        get_report_view=lambda report_id, user_id: report,
        resolve_download=lambda **kwargs: DownloadResolution(document=document, absolute_path=str(artifact)),
    )
    with TornadoTestClient(create_app(frontend_dir=str(tmp_path), container=FakeWebContainer(report_service=service)), headers={"X-User-Id": "user"}) as client:
        response = client.get("/rest/chatbi/v1/reports/rpt_1/documents/doc_1/download")
        assert response.status_code == 200
        assert response.text == "# report\n"


def test_report_document_validation_error_uses_public_error(tmp_path):
    service = SimpleNamespace(generate_documents=lambda **kwargs: (_ for _ in ()).throw(ValidationError("PDF export is not available yet")))
    with TornadoTestClient(create_app(frontend_dir=str(tmp_path), container=FakeWebContainer(report_service=service)), headers={"X-User-Id": "user"}) as client:
        response = client.post("/rest/chatbi/v1/reports/rpt_1/document-generations", json={"formats": ["pdf"]})
        assert response.status_code == 400
        assert response.json()["errorCode"] == "chatbi.base.param.invalid"
