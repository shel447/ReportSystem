from types import SimpleNamespace

from src.contexts.report.application.generation_models import DocumentGenerationResult
from src.main import create_app
from tests.support.tornado_client import FakeWebContainer, TornadoTestClient


def test_document_generation_handler_returns_application_result(tmp_path):
    result = DocumentGenerationResult(report_id="rpt_1", jobs=[], documents=[])
    service = SimpleNamespace(generate_documents=lambda **kwargs: result)
    with TornadoTestClient(create_app(frontend_dir=str(tmp_path), container=FakeWebContainer(report_service=service)), headers={"X-User-Id": "user"}) as client:
        response = client.post("/rest/chatbi/v1/reports/rpt_1/document-generations", json={"formats": ["word"]})
        assert response.status_code == 200
        assert response.json()["reportId"] == "rpt_1"
