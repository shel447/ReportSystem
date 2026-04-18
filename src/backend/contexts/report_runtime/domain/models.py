"""报告运行时聚合的领域模型：模板实例、报告实例与导出产物。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class TemplateInstance:
    """运行时聚合，持续维护一条报告对话对应的模板实例状态。"""

    id: str
    schema_version: str
    template_id: str
    conversation_id: str
    chat_id: str | None
    status: str
    capture_stage: str
    revision: int
    parameter_values: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    catalogs: list[dict[str, Any]] = field(default_factory=list)
    delta_views: list[dict[str, Any]] = field(default_factory=list)
    template_skeleton_status: dict[str, str] = field(default_factory=dict)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class ReportInstance:
    """冻结后的报告资源，内部承载最终报告结构。"""

    id: str
    template_id: str
    template_instance_id: str
    user_id: str
    source_conversation_id: str | None
    source_chat_id: str | None
    status: str
    schema_version: str
    report: dict[str, Any]
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class DocumentArtifact:
    """报告作用域下的导出文件元数据。"""

    id: str
    report_instance_id: str
    artifact_kind: str
    source_format: str | None
    generation_mode: str
    mime_type: str
    storage_key: str
    status: str
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class ExportJob:
    """文档导出流水线中单一格式的一次执行记录。"""

    id: str
    report_instance_id: str
    current_format: str
    status: str
    dependency_job_id: str | None = None
    exporter_backend: str = "local"
    request_payload_hash: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None
