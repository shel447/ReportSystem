"""CLI adapter for the Java Office exporter."""

from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path

from ...contexts.report.application.generation_models import GeneratedArtifact
from ...contexts.report.domain.generation_models import ReportDsl, report_dsl_to_dict
from ...shared.kernel.errors import ValidationError
from ...shared.kernel.paths import generated_documents_dir, project_root

EXPORTER_DIR = project_root() / "modules" / "exporter"
EXPORTER_SOURCE_DIR = EXPORTER_DIR / "src" / "main" / "java"
EXPORTER_JAR_PATH = EXPORTER_DIR / "target" / "report-exporter-0.1.0.jar"
MIME_TYPES = {
    "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "ppt": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
TARGETS = {"word": "docx", "ppt": "pptx"}
EXTENSIONS = {"word": ".docx", "ppt": ".pptx"}


class JavaOfficeExporterGateway:
    """Invoke the exporter CLI synchronously and return the generated artifact."""

    def export(
        self,
        *,
        report: ReportDsl,
        report_id: str,
        format_name: str,
        theme: str,
        strict_validation: bool,
        pdf_source: str | None,
    ) -> GeneratedArtifact:
        normalized_format = str(format_name or "").strip().lower()
        if normalized_format == "pdf":
            raise ValidationError("PDF export is not available yet")
        if normalized_format not in TARGETS:
            raise ValidationError(f"Unsupported office document format: {format_name}")

        self._build_if_needed()
        documents_dir = generated_documents_dir()
        input_dir = documents_dir / "exporter-inputs"
        artifact_dir = documents_dir / "exporter-artifacts"
        input_dir.mkdir(parents=True, exist_ok=True)
        artifact_dir.mkdir(parents=True, exist_ok=True)

        suffix = uuid.uuid4().hex[:12]
        input_path = input_dir / f"{report_id}-{suffix}.json"
        file_name = f"{report_id}-{suffix}{EXTENSIONS[normalized_format]}"
        output_path = artifact_dir / file_name
        input_path.write_text(
            json.dumps(report_dsl_to_dict(report), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        command = [
            "java",
            "-jar",
            str(EXPORTER_JAR_PATH),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--target",
            TARGETS[normalized_format],
        ]
        if theme:
            command.extend(["--theme", theme])
        if strict_validation:
            command.append("--strict")
        subprocess.run(command, check=True, cwd=str(EXPORTER_DIR))
        if not output_path.exists():
            raise RuntimeError(f"Exporter completed without output file: {output_path}")
        return GeneratedArtifact(
            file_name=file_name,
            storage_key=str(output_path),
            mime_type=MIME_TYPES[normalized_format],
        )

    def _build_if_needed(self) -> None:
        java_files = list(EXPORTER_SOURCE_DIR.rglob("*.java"))
        if not java_files:
            raise RuntimeError("Java office exporter source files not found")
        latest_source_mtime = max(item.stat().st_mtime for item in java_files)
        if EXPORTER_JAR_PATH.exists() and EXPORTER_JAR_PATH.stat().st_mtime >= latest_source_mtime:
            return
        subprocess.run(
            [_find_maven(), "clean", "package", "-q", "-DskipTests"],
            check=True,
            cwd=str(EXPORTER_DIR),
        )
        if not EXPORTER_JAR_PATH.exists():
            raise RuntimeError(f"Maven build succeeded but JAR not found: {EXPORTER_JAR_PATH}")


def _find_maven() -> str:
    mvnw = EXPORTER_DIR / "mvnw"
    if mvnw.exists():
        return str(mvnw)
    mvnw_cmd = EXPORTER_DIR / "mvnw.cmd"
    if mvnw_cmd.exists():
        return str(mvnw_cmd)
    return "mvn"
