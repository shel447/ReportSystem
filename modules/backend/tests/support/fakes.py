from __future__ import annotations

from src.contexts.report.application.generation_models import GeneratedArtifact


class FakeOfficeExporter:
    def __init__(self, *, storage_key: str = "/tmp/demo.docx") -> None:
        self.storage_key = storage_key
        self.calls: list[dict[str, object]] = []

    def export(self, **kwargs) -> GeneratedArtifact:
        self.calls.append(kwargs)
        return GeneratedArtifact(
            file_name="demo.docx",
            storage_key=self.storage_key,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
