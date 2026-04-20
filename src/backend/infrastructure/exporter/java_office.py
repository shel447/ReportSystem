from __future__ import annotations

import os
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from ...contexts.report_runtime.domain.models import ReportDsl, report_dsl_to_dict

EXPORTER_BASE_URL = os.environ.get("REPORT_EXPORTER_BASE_URL", "http://127.0.0.1:18500").rstrip("/")
EXPORTER_HOST = os.environ.get("REPORT_EXPORTER_HOST", "127.0.0.1")
EXPORTER_PORT = int(os.environ.get("REPORT_EXPORTER_PORT", "18500"))
EXPORTER_TIMEOUT_SECONDS = float(os.environ.get("REPORT_EXPORTER_TIMEOUT_SECONDS", "30"))
EXPORTER_DIR = Path(__file__).resolve().parents[4] / "services" / "java-office-exporter"
EXPORTER_SOURCE_DIR = EXPORTER_DIR / "src"
EXPORTER_BUILD_DIR = EXPORTER_DIR / "build" / "classes"
EXPORTER_ARTIFACTS_DIR = EXPORTER_DIR / "artifacts"
EXPORTER_LOG_DIR = Path(__file__).resolve().parents[4] / "output" / "runtime"
EXPORTER_MAIN_CLASS = "report.system.exporter.JavaOfficeExporterServer"

_START_LOCK = threading.Lock()
_EXPORTER_PROCESS: subprocess.Popen[bytes] | None = None


class JavaOfficeExporterGateway:
    def export(
        self,
        *,
        report: ReportDsl,
        report_id: str,
        format_name: str,
        theme: str,
        strict_validation: bool,
        pdf_source: str | None,
    ) -> dict[str, Any]:
        self._ensure_service()
        report_payload = report_dsl_to_dict(report)
        payload = {
            "requestId": f"req_export_{uuid.uuid4().hex[:12]}",
            "reportId": report_id,
            "dslSchemaVersion": str(report.basic_info.schema_version or ""),
            "reportDsl": report_payload,
            "options": {
                "theme": theme,
                "strictValidation": strict_validation,
                "pdfSource": pdf_source,
            },
        }
        with httpx.Client(timeout=EXPORTER_TIMEOUT_SECONDS) as client:
            response = client.post(f"{EXPORTER_BASE_URL}/exports/{format_name}", json=payload)
            response.raise_for_status()
            data = response.json()
        artifact = data.get("artifact") or {}
        return {
            "fileName": str(artifact.get("fileName") or f"{report_id}-{format_name}"),
            "storageKey": str(artifact.get("storageKey") or ""),
            "mimeType": str(artifact.get("contentType") or "application/octet-stream"),
        }

    def _ensure_service(self) -> None:
        if self._is_healthy():
            return
        with _START_LOCK:
            if self._is_healthy():
                return
            self._compile_sources_if_needed()
            self._start_local_process_if_needed()
            deadline = time.time() + 20
            while time.time() < deadline:
                if self._is_healthy():
                    return
                time.sleep(0.5)
        raise RuntimeError("Java office exporter is not available")

    def _is_healthy(self) -> bool:
        try:
            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{EXPORTER_BASE_URL}/health")
                if response.status_code != 200:
                    return False
                payload = response.json()
                return str(payload.get("status") or "") == "ok"
        except Exception:
            return False

    def _compile_sources_if_needed(self) -> None:
        java_files = list(EXPORTER_SOURCE_DIR.rglob("*.java"))
        if not java_files:
            raise RuntimeError("Java office exporter source files not found")
        class_file = EXPORTER_BUILD_DIR / "report" / "system" / "exporter" / "JavaOfficeExporterServer.class"
        latest_source_mtime = max(item.stat().st_mtime for item in java_files)
        if class_file.exists() and class_file.stat().st_mtime >= latest_source_mtime:
            return
        EXPORTER_BUILD_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["javac", "-encoding", "UTF-8", "-d", str(EXPORTER_BUILD_DIR), *[str(item) for item in java_files]],
            check=True,
            cwd=str(EXPORTER_DIR),
        )

    def _start_local_process_if_needed(self) -> None:
        global _EXPORTER_PROCESS
        if _EXPORTER_PROCESS is not None and _EXPORTER_PROCESS.poll() is None:
            return
        EXPORTER_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        EXPORTER_LOG_DIR.mkdir(parents=True, exist_ok=True)
        stdout_path = EXPORTER_LOG_DIR / "java-office-exporter.out.log"
        stderr_path = EXPORTER_LOG_DIR / "java-office-exporter.err.log"
        stdout_handle = open(stdout_path, "ab")
        stderr_handle = open(stderr_path, "ab")
        _EXPORTER_PROCESS = subprocess.Popen(
            [
                "java",
                "-cp",
                str(EXPORTER_BUILD_DIR),
                EXPORTER_MAIN_CLASS,
                "--host",
                EXPORTER_HOST,
                "--port",
                str(EXPORTER_PORT),
                "--artifacts-dir",
                str(EXPORTER_ARTIFACTS_DIR),
            ],
            cwd=str(EXPORTER_DIR),
            stdout=stdout_handle,
            stderr=stderr_handle,
        )
