"""使用持久化框架保存运行时聚合，并避免对象映射细节向上层泄漏。"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from ....infrastructure.persistence.models import ExportJob as ExportJobRow
from ....infrastructure.persistence.models import ReportDocument as ReportDocumentRow
from ....infrastructure.persistence.models import ReportInstance as ReportInstanceRow
from ....infrastructure.persistence.models import ReportTemplate as ReportTemplateRow
from ....infrastructure.persistence.models import TemplateInstance as TemplateInstanceRow
from ....shared.kernel.errors import NotFoundError
from ...template_catalog.domain.models import ReportTemplate
from ..domain.models import DocumentArtifact, ExportJob, ReportInstance, TemplateInstance
from ..domain.services import serialize_template_instance


class SqlAlchemyRuntimeTemplateRepository:
    """供报告运行时读取模板的只读适配器。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, template_id: str) -> ReportTemplate | None:
        row = self.db.get(ReportTemplateRow, template_id)
        if row is None:
            return None
        payload = dict(row.content or {})
        return ReportTemplate(
            id=row.id,
            category=row.category,
            name=row.name,
            description=row.description or "",
            schema_version=row.schema_version,
            parameters=list(payload.get("parameters") or []),
            catalogs=list(payload.get("catalogs") or []),
            tags=list(payload.get("tags") or []),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class SqlAlchemyTemplateInstanceRepository:
    """模板实例运行时聚合的持久化适配器。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, instance: TemplateInstance, *, user_id: str) -> TemplateInstance:
        payload = serialize_template_instance(instance)
        row = TemplateInstanceRow(
            id=instance.id,
            template_id=instance.template_id,
            conversation_id=instance.conversation_id,
            chat_id=instance.chat_id,
            user_id=user_id,
            status=instance.status,
            capture_stage=instance.capture_stage,
            revision=instance.revision,
            schema_version=instance.schema_version,
            content=payload,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return _to_template_instance(row)

    def update(self, instance: TemplateInstance, *, user_id: str) -> TemplateInstance:
        row = self.db.get(TemplateInstanceRow, instance.id)
        if row is None or row.user_id != user_id:
            raise NotFoundError("Template instance not found")
        row.chat_id = instance.chat_id
        row.status = instance.status
        row.capture_stage = instance.capture_stage
        row.revision = instance.revision
        row.schema_version = instance.schema_version
        row.content = serialize_template_instance(instance)
        row.updated_at = datetime.now(timezone.utc).replace(microsecond=0)
        self.db.commit()
        self.db.refresh(row)
        return _to_template_instance(row)

    def get(self, instance_id: str, *, user_id: str) -> TemplateInstance | None:
        row = self.db.get(TemplateInstanceRow, instance_id)
        if row is None or row.user_id != user_id:
            return None
        return _to_template_instance(row)

    def get_latest_for_conversation(self, conversation_id: str, *, user_id: str) -> TemplateInstance | None:
        row = (
            self.db.query(TemplateInstanceRow)
            .filter(
                TemplateInstanceRow.conversation_id == conversation_id,
                TemplateInstanceRow.user_id == user_id,
            )
            .order_by(TemplateInstanceRow.updated_at.desc(), TemplateInstanceRow.created_at.desc())
            .first()
        )
        return _to_template_instance(row) if row else None


class SqlAlchemyReportInstanceRepository:
    """冻结后报告资源的持久化适配器。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        report_id: str,
        template_id: str,
        template_instance_id: str,
        user_id: str,
        source_conversation_id: str | None,
        source_chat_id: str | None,
        status: str,
        schema_version: str,
        report: dict[str, Any],
    ) -> ReportInstance:
        row = ReportInstanceRow(
            id=report_id,
            template_id=template_id,
            template_instance_id=template_instance_id,
            user_id=user_id,
            source_conversation_id=source_conversation_id,
            source_chat_id=source_chat_id,
            status=status,
            schema_version=schema_version,
            content=report,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return _to_report_instance(row)

    def get(self, report_id: str, *, user_id: str) -> ReportInstance | None:
        row = self.db.get(ReportInstanceRow, report_id)
        if row is None or row.user_id != user_id:
            return None
        return _to_report_instance(row)

    def update_status(self, report_id: str, *, user_id: str, status: str, report: dict[str, Any] | None = None) -> ReportInstance:
        row = self.db.get(ReportInstanceRow, report_id)
        if row is None or row.user_id != user_id:
            raise NotFoundError("Report not found")
        row.status = status
        if report is not None:
            row.content = report
        row.updated_at = datetime.now(timezone.utc).replace(microsecond=0)
        self.db.commit()
        self.db.refresh(row)
        return _to_report_instance(row)


class SqlAlchemyDocumentRepository:
    """报告作用域文档产物的持久化适配器。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        report_instance_id: str,
        artifact_kind: str,
        source_format: str | None,
        generation_mode: str,
        mime_type: str,
        storage_key: str,
        status: str,
        error_message: str | None = None,
    ) -> DocumentArtifact:
        row = ReportDocumentRow(
            report_instance_id=report_instance_id,
            artifact_kind=artifact_kind,
            source_format=source_format,
            generation_mode=generation_mode,
            mime_type=mime_type,
            storage_key=storage_key,
            status=status,
            error_message=error_message,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return _to_document(row)

    def list_by_report(self, report_instance_id: str) -> list[DocumentArtifact]:
        rows = (
            self.db.query(ReportDocumentRow)
            .filter(ReportDocumentRow.report_instance_id == report_instance_id)
            .order_by(ReportDocumentRow.created_at.desc())
            .all()
        )
        return [_to_document(row) for row in rows]

    def get_for_report(self, report_instance_id: str, document_id: str) -> DocumentArtifact | None:
        row = (
            self.db.query(ReportDocumentRow)
            .filter(
                ReportDocumentRow.report_instance_id == report_instance_id,
                ReportDocumentRow.id == document_id,
            )
            .first()
        )
        return _to_document(row) if row else None


class SqlAlchemyExportJobRepository:
    """导出编排任务的持久化适配器。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        report_instance_id: str,
        current_format: str,
        status: str,
        dependency_job_id: str | None,
        exporter_backend: str,
        request_payload_hash: str,
    ) -> ExportJob:
        row = ExportJobRow(
            report_instance_id=report_instance_id,
            current_format=current_format,
            status=status,
            dependency_job_id=dependency_job_id,
            exporter_backend=exporter_backend,
            request_payload_hash=request_payload_hash,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return _to_export_job(row)


def _to_template_instance(row: TemplateInstanceRow) -> TemplateInstance:
    # 内容字段是运行时树结构的事实来源；顶层列只保留仓储查询需要的索引字段。
    payload = copy.deepcopy(row.content or {})
    return TemplateInstance(
        id=row.id,
        schema_version=str(payload.get("schemaVersion") or row.schema_version),
        template_id=row.template_id,
        template=copy.deepcopy(payload.get("template") or {}),
        conversation_id=row.conversation_id,
        chat_id=row.chat_id,
        status=row.status,
        capture_stage=row.capture_stage,
        revision=int(row.revision or 1),
        parameters=copy.deepcopy(payload.get("parameters") or []),
        parameter_confirmation=copy.deepcopy(payload.get("parameterConfirmation") or {}),
        catalogs=copy.deepcopy(payload.get("catalogs") or []),
        warnings=copy.deepcopy(payload.get("warnings") or []),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_report_instance(row: ReportInstanceRow) -> ReportInstance:
    return ReportInstance(
        id=row.id,
        template_id=row.template_id,
        template_instance_id=row.template_instance_id,
        user_id=row.user_id,
        source_conversation_id=row.source_conversation_id,
        source_chat_id=row.source_chat_id,
        status=row.status,
        schema_version=row.schema_version,
        report=copy.deepcopy(row.content or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_document(row: ReportDocumentRow) -> DocumentArtifact:
    return DocumentArtifact(
        id=row.id,
        report_instance_id=row.report_instance_id,
        artifact_kind=row.artifact_kind,
        source_format=row.source_format,
        generation_mode=row.generation_mode,
        mime_type=row.mime_type,
        storage_key=row.storage_key,
        status=row.status,
        error_message=row.error_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_export_job(row: ExportJobRow) -> ExportJob:
    return ExportJob(
        id=row.id,
        report_instance_id=row.report_instance_id,
        current_format=row.current_format,
        status=row.status,
        dependency_job_id=row.dependency_job_id,
        exporter_backend=row.exporter_backend,
        request_payload_hash=row.request_payload_hash or "",
        started_at=row.started_at,
        finished_at=row.finished_at,
        error_code=row.error_code,
        error_message=row.error_message,
    )
