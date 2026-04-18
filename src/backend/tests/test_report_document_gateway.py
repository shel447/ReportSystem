import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.contexts.report_runtime.infrastructure.documents import ReportDocumentGateway
from backend.contexts.report_runtime.domain.models import DocumentArtifact


class _FakeOfficeExporter:
    def __init__(self):
        self.calls = []

    def export(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "fileName": "demo.docx",
            "storageKey": "C:/tmp/demo.docx",
            "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }


class ReportDocumentGatewayTests(unittest.TestCase):
    def test_word_generation_delegates_to_java_exporter(self):
        exporter = _FakeOfficeExporter()
        gateway = ReportDocumentGateway(office_exporter=exporter)

        result = gateway.generate_document(
            report={"basicInfo": {"schemaVersion": "1.0.0"}},
            report_id="rpt_001",
            format_name="word",
            theme="default",
            strict_validation=True,
            pdf_source="word",
        )

        self.assertEqual(result["fileName"], "demo.docx")
        self.assertEqual(len(exporter.calls), 1)
        self.assertEqual(exporter.calls[0]["format_name"], "word")

    def test_markdown_generation_writes_local_file(self):
        exporter = _FakeOfficeExporter()
        gateway = ReportDocumentGateway(office_exporter=exporter)

        result = gateway.generate_document(
            report={"basicInfo": {"schemaVersion": "1.0.0", "name": "demo"}},
            report_id="rpt_002",
            format_name="markdown",
            theme="default",
            strict_validation=True,
            pdf_source=None,
        )

        self.assertTrue(result["storageKey"].endswith(".md"))
        self.assertEqual(exporter.calls, [])
        self.assertTrue(Path(result["storageKey"]).exists())

    def test_resolve_download_returns_file_metadata(self):
        with TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "demo.md"
            target.write_text("# demo\n", encoding="utf-8")
            gateway = ReportDocumentGateway(office_exporter=_FakeOfficeExporter())
            document = DocumentArtifact(
                id="doc_001",
                report_instance_id="rpt_001",
                artifact_kind="markdown",
                source_format=None,
                generation_mode="sync",
                mime_type="text/markdown",
                storage_key=str(target),
                status="ready",
            )

            metadata, absolute_path = gateway.resolve_download(document)

        self.assertEqual(metadata["id"], "doc_001")
        self.assertEqual(absolute_path, str(target))


if __name__ == "__main__":
    unittest.main()
