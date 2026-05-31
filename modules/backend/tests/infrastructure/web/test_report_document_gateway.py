import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.contexts.report.application.generation_models import GeneratedArtifact
from src.contexts.report.infrastructure.documents import ReportDocumentGateway
from src.contexts.report.domain.generation_models import DocumentArtifact, report_dsl_from_dict
from src.infrastructure.exporter import java_office as gateway_module
from src.infrastructure.exporter.java_office import JavaOfficeExporterGateway
from src.shared.kernel.errors import ValidationError
from src.shared.kernel.paths import generated_documents_dir


class _FakeOfficeExporter:
    def __init__(self):
        self.calls = []

    def export(self, **kwargs):
        self.calls.append(kwargs)
        return GeneratedArtifact(
            file_name="demo.docx",
            storage_key="C:/tmp/demo.docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


class ReportDocumentGatewayTests(unittest.TestCase):
    def test_word_generation_delegates_to_java_exporter(self):
        exporter = _FakeOfficeExporter()
        gateway = ReportDocumentGateway(office_exporter=exporter)
        report = report_dsl_from_dict(
            {
                "basicInfo": {"id": "rpt_001", "schemaVersion": "1.0.0", "mode": "published", "status": "Success"},
                "catalogs": [],
                "layout": {"type": "grid", "grid": {"cols": 12, "rowHeight": 24}},
            }
        )

        result = gateway.generate_document(
            report=report,
            report_id="rpt_001",
            format_name="word",
            theme="default",
            strict_validation=True,
            pdf_source="word",
        )

        self.assertEqual(result.file_name, "demo.docx")
        self.assertEqual(len(exporter.calls), 1)
        self.assertEqual(exporter.calls[0]["format_name"], "word")

    def test_markdown_generation_writes_local_file(self):
        exporter = _FakeOfficeExporter()
        gateway = ReportDocumentGateway(office_exporter=exporter)
        report = report_dsl_from_dict(
            {
                "basicInfo": {"id": "rpt_002", "schemaVersion": "1.0.0", "mode": "published", "status": "Success", "name": "demo"},
                "catalogs": [],
                "layout": {"type": "grid", "grid": {"cols": 12, "rowHeight": 24}},
            }
        )

        result = gateway.generate_document(
            report=report,
            report_id="rpt_002",
            format_name="markdown",
            theme="default",
            strict_validation=True,
            pdf_source=None,
        )

        self.assertTrue(result.storage_key.endswith(".md"))
        self.assertEqual(exporter.calls, [])
        self.assertTrue(Path(result.storage_key).exists())

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

            resolution = gateway.resolve_download(document)

        self.assertEqual(resolution.document.id, "doc_001")
        self.assertEqual(resolution.absolute_path, str(target))

    def test_pdf_generation_is_rejected_explicitly(self):
        gateway = ReportDocumentGateway(office_exporter=_FakeOfficeExporter())
        with self.assertRaisesRegex(ValidationError, "PDF export is not available yet"):
            gateway.generate_document(
                report=report_dsl_from_dict(
                    {
                        "basicInfo": {"id": "rpt_pdf", "schemaVersion": "1.0.0", "mode": "published", "status": "Success"},
                        "catalogs": [],
                        "layout": {"type": "grid", "grid": {"cols": 12, "rowHeight": 24}},
                    }
                ),
                report_id="rpt_pdf",
                format_name="pdf",
                theme="default",
            )

    def test_java_gateway_invokes_cli_and_writes_to_runtime_data_dir(self):
        report = report_dsl_from_dict(
            {
                "basicInfo": {"id": "rpt_cli", "schemaVersion": "1.0.0", "mode": "published", "status": "Success"},
                "catalogs": [],
                "layout": {"type": "grid", "grid": {"cols": 12, "rowHeight": 24}},
            }
        )

        def fake_run(command, **kwargs):
            output_path = Path(command[command.index("--output") + 1])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"docx")

        gateway = JavaOfficeExporterGateway()
        with patch.object(gateway, "_build_if_needed"), patch("src.infrastructure.exporter.java_office.subprocess.run", side_effect=fake_run) as run:
            artifact = gateway.export(
                report=report,
                report_id="rpt_cli",
                format_name="word",
                theme="default",
                strict_validation=True,
                pdf_source=None,
            )

        command = run.call_args.args[0]
        self.assertEqual(command[:3], ["java", "-jar", str(gateway_module.EXPORTER_JAR_PATH)])
        self.assertIn("--target", command)
        self.assertEqual(command[command.index("--target") + 1], "docx")
        self.assertIn("--strict", command)
        self.assertTrue(Path(artifact.storage_key).is_relative_to(generated_documents_dir()))


if __name__ == "__main__":
    unittest.main()
