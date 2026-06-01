from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pytest

from src.infrastructure.exporter.java_office import JavaOfficeExporterGateway
from tests.support.mock_external import compile_complex_template


@pytest.mark.exporter_e2e
@pytest.mark.parametrize(
    ("template_name", "format_name", "required_entry", "chart_prefix", "expected_text"),
    [
        ("network-device-health-inspection-flow.json", "word", "word/document.xml", "word/charts/chart", "核心交换机-A"),
        ("network-operations-status-flow.json", "word", "word/document.xml", "word/charts/chart", "严重"),
        ("network-device-health-inspection-paged.json", "ppt", "ppt/presentation.xml", "ppt/charts/chart", "核心交换机-A"),
        ("network-operations-status-paged.json", "ppt", "ppt/presentation.xml", "ppt/charts/chart", "严重"),
    ],
)
def test_complex_mock_template_exports_real_office_package(template_name, format_name, required_entry, chart_prefix, expected_text):
    report = compile_complex_template(template_name)
    artifact = JavaOfficeExporterGateway().export(
        report=report,
        report_id=f"e2e_{report.basic_info.id}",
        format_name=format_name,
        theme="default",
        strict_validation=False,
        pdf_source=None,
    )

    output_path = Path(artifact.storage_key)
    assert ".test" in output_path.parts
    assert output_path.exists()
    with ZipFile(output_path) as package:
        names = package.namelist()
        assert required_entry in names
        assert any(name.startswith(chart_prefix) for name in names)
        assert any("/embeddings/" in name for name in names)
        relationship_xml = b"".join(package.read(name) for name in names if name.endswith(".rels"))
        assert b"/relationships/chart" in relationship_xml
        document_xml = b"".join(package.read(name) for name in names if name.endswith(".xml"))
        assert expected_text.encode("utf-8") in document_xml
