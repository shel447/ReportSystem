from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from ..domain.models import ReportInstance, TemplateInstance as TemplateInstanceEntity
from ...template_catalog.domain.models import ReportTemplate
from ....infrastructure.persistence.models import ReportDocument, ReportInstance as ReportInstanceModel, ReportTemplate as ReportTemplateModel, TemplateInstance as TemplateInstanceModel, gen_id


class SqlAlchemyRuntimeTemplateRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, template_id: str) -> ReportTemplate | None:
        row = self.db.query(ReportTemplateModel).filter(ReportTemplateModel.template_id == template_id).first()
        return _to_template(row) if row else None


class SqlAlchemyReportInstanceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        template_id: str,
        template_version: str,
        input_params: dict[str, Any],
        outline_content: list[dict[str, Any]],
        status: str = "draft",
        report_time=None,
        report_time_source: str = "",
        user_id: str = "default",
        source_session_id: str | None = None,
        source_message_id: str | None = None,
    ) -> ReportInstance:
        row = ReportInstanceModel(
            instance_id=gen_id(),
            template_id=template_id,
            template_version=template_version,
            status=status,
            user_id=user_id or "default",
            source_session_id=source_session_id,
            source_message_id=source_message_id,
            input_params=input_params,
            outline_content=outline_content,
            report_time=report_time,
            report_time_source=report_time_source,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return _to_instance(row)

    def get(self, instance_id: str, user_id: str | None = None) -> ReportInstance | None:
        query = self.db.query(ReportInstanceModel).filter(ReportInstanceModel.instance_id == instance_id)
        if user_id:
            query = query.filter(ReportInstanceModel.user_id == user_id)
        row = query.first()
        return _to_instance(row) if row else None

    def list(self, template_id: str | None = None, user_id: str | None = None) -> list[ReportInstance]:
        query = self.db.query(ReportInstanceModel)
        if template_id:
            query = query.filter(ReportInstanceModel.template_id == template_id)
        if user_id:
            query = query.filter(ReportInstanceModel.user_id == user_id)
        return [_to_instance(row) for row in query.order_by(ReportInstanceModel.created_at.desc()).all()]

    def update_fields(self, instance_id: str, updates: dict[str, Any], user_id: str | None = None) -> ReportInstance:
        query = self.db.query(ReportInstanceModel).filter(ReportInstanceModel.instance_id == instance_id)
        if user_id:
            query = query.filter(ReportInstanceModel.user_id == user_id)
        row = query.first()
        if not row:
            raise LookupError("Instance not found")
        for key, value in updates.items():
            setattr(row, key, value)
        self.db.commit()
        self.db.refresh(row)
        return _to_instance(row)

    def replace_outline_section(self, instance_id: str, section_index: int, section_payload: dict[str, Any], user_id: str | None = None) -> ReportInstance:
        query = self.db.query(ReportInstanceModel).filter(ReportInstanceModel.instance_id == instance_id)
        if user_id:
            query = query.filter(ReportInstanceModel.user_id == user_id)
        row = query.first()
        if not row:
            raise LookupError("Instance not found")
        content = list(row.outline_content or [])
        content[section_index] = section_payload
        row.outline_content = content
        self.db.commit()
        self.db.refresh(row)
        return _to_instance(row)

    def delete(self, instance_id: str, user_id: str | None = None) -> None:
        query = self.db.query(ReportInstanceModel).filter(ReportInstanceModel.instance_id == instance_id)
        if user_id:
            query = query.filter(ReportInstanceModel.user_id == user_id)
        row = query.first()
        if not row:
            raise LookupError("Instance not found")
        self.db.delete(row)
        self.db.commit()

    def get_input_params(self, instance_id: str) -> dict[str, Any] | None:
        row = self.db.query(ReportInstanceModel).filter(ReportInstanceModel.instance_id == instance_id).first()
        return deepcopy(row.input_params or {}) if row else None


class SqlAlchemyTemplateInstanceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_instance(self, instance_id: str) -> TemplateInstanceEntity | None:
        row = (
            self.db.query(TemplateInstanceModel)
            .filter(TemplateInstanceModel.report_instance_id == instance_id)
            .order_by(TemplateInstanceModel.created_at.desc(), TemplateInstanceModel.template_instance_id.desc())
            .first()
        )
        return _to_template_instance(row) if row else None

    def list_map_by_instances(self, instance_ids: list[str]) -> dict[str, TemplateInstanceEntity]:
        if not instance_ids:
            return {}
        rows = (
            self.db.query(TemplateInstanceModel)
            .filter(TemplateInstanceModel.report_instance_id.in_(instance_ids))
            .order_by(TemplateInstanceModel.created_at.desc(), TemplateInstanceModel.template_instance_id.desc())
            .all()
        )
        mapping: dict[str, TemplateInstanceEntity] = {}
        for row in rows:
            if row.report_instance_id in mapping:
                continue
            mapping[row.report_instance_id] = _to_template_instance(row)
        return mapping

    def delete_by_instance(self, instance_id: str) -> None:
        rows = self.db.query(TemplateInstanceModel).filter(TemplateInstanceModel.report_instance_id == instance_id).all()
        for row in rows:
            self.db.delete(row)
        self.db.commit()

    def save_runtime_updates(
        self,
        *,
        report_instance_id: str,
        outline_snapshot: list[dict[str, Any]] | None = None,
        generated_sections: list[dict[str, Any]] | None = None,
        generated_document: dict[str, Any] | None = None,
        status: str | None = None,
    ) -> TemplateInstanceEntity | None:
        row = (
            self.db.query(TemplateInstanceModel)
            .filter(TemplateInstanceModel.report_instance_id == report_instance_id)
            .order_by(TemplateInstanceModel.created_at.desc(), TemplateInstanceModel.template_instance_id.desc())
            .first()
        )
        if not row:
            return None
        content = deepcopy(row.content or {})
        legacy_outline = list(outline_snapshot) if outline_snapshot is not None else list(row.outline_snapshot or [])
        content["outline_snapshot"] = legacy_outline
        content.setdefault("runtime_state", {}).setdefault("outline_runtime", {})["current_outline_instance"] = deepcopy(legacy_outline)
        content.setdefault("resolved_view", {})["outline"] = deepcopy(legacy_outline)
        if generated_sections is not None:
            content.setdefault("generated_content", {})["sections"] = deepcopy(generated_sections)
        if generated_document is not None:
            docs = list(content.setdefault("generated_content", {}).get("documents") or [])
            docs.append(deepcopy(generated_document))
            content["generated_content"]["documents"] = docs
        instance_meta = content.setdefault("instance_meta", {})
        instance_meta["revision"] = max(1, int(instance_meta.get("revision") or 1) + 1)
        if status:
            instance_meta["status"] = status
        instance_meta["updated_at"] = datetime.now(UTC).isoformat()
        row.content = content
        if status:
            row.capture_stage = _status_to_capture_stage(status)
        self.db.commit()
        self.db.refresh(row)
        return _to_template_instance(row)


class SqlAlchemyDocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, instance_id: str | None = None) -> list[ReportDocument]:
        query = self.db.query(ReportDocument)
        if instance_id:
            query = query.filter(ReportDocument.instance_id == instance_id)
        return query.order_by(ReportDocument.created_at.desc()).all()

    def get(self, document_id: str) -> ReportDocument | None:
        return self.db.query(ReportDocument).filter(ReportDocument.document_id == document_id).first()

    def delete(self, document_id: str) -> ReportDocument | None:
        row = self.get(document_id)
        if row:
            self.db.delete(row)
            self.db.commit()
        return row


def _to_instance(row: ReportInstanceModel) -> ReportInstance:
    return ReportInstance(
        instance_id=row.instance_id,
        template_id=row.template_id,
        status=row.status,
        user_id=row.user_id or "default",
        source_session_id=row.source_session_id,
        source_message_id=row.source_message_id,
        input_params=deepcopy(row.input_params or {}),
        outline_content=deepcopy(row.outline_content or []),
        report_time=row.report_time,
        report_time_source=row.report_time_source or "",
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_template(row: ReportTemplateModel) -> ReportTemplate:
    return ReportTemplate(
        id=row.template_id,
        category=row.category or "",
        name=row.name,
        description=row.description or "",
        parameters=list(row.parameters or []),
        sections=list(row.sections or []),
        version=row.version or "1.0",
        created_at=row.created_at,
    )


def _to_template_instance(row: TemplateInstanceModel) -> TemplateInstanceEntity:
    content = deepcopy(row.content or {})
    template_row = row
    base_template_payload = content.get("base_template") if isinstance(content.get("base_template"), dict) else {}
    base_template = ReportTemplate(
        id=str(base_template_payload.get("id") or row.template_id),
        category=str(base_template_payload.get("category") or ""),
        name=str(base_template_payload.get("name") or row.template_name or ""),
        description=str(base_template_payload.get("description") or ""),
        parameters=list(base_template_payload.get("parameters") or []),
        sections=list(base_template_payload.get("sections") or []),
        version=row.template_version or "1.0",
        created_at=getattr(template_row, "created_at", None),
    )
    instance_meta = content.get("instance_meta") if isinstance(content.get("instance_meta"), dict) else {}
    runtime_state = content.get("runtime_state") if isinstance(content.get("runtime_state"), dict) else {}
    resolved_view = content.get("resolved_view") if isinstance(content.get("resolved_view"), dict) else {}
    generated_content = content.get("generated_content") if isinstance(content.get("generated_content"), dict) else {}
    fragments = content.get("fragments") if isinstance(content.get("fragments"), dict) else {}
    return TemplateInstanceEntity(
        template_instance_id=row.template_instance_id,
        template_id=row.template_id,
        template_name=row.template_name or row.template_id,
        session_id=row.session_id or "",
        capture_stage=row.capture_stage or "",
        base_template=base_template,
        schema_version=str(content.get("schema_version") or row.schema_version or "ti.v1.0"),
        status=str(instance_meta.get("status") or _capture_stage_to_status(row.capture_stage)),
        revision=max(1, int(instance_meta.get("revision") or 1)),
        input_params_snapshot=deepcopy(row.input_params_snapshot or {}),
        outline_snapshot=deepcopy(row.outline_snapshot or []),
        resolved_view=deepcopy(resolved_view),
        runtime_state=deepcopy(runtime_state),
        generated_content=deepcopy(generated_content),
        fragments=deepcopy(fragments),
        warnings=list(row.warnings or []),
        report_instance_id=row.report_instance_id,
        created_at=row.created_at,
    )


def _status_to_capture_stage(status: str) -> str:
    normalized = str(status or "").strip()
    if normalized in {"completed", "generating"}:
        return "generation_baseline"
    if normalized in {"ready_for_confirmation", "confirmed"}:
        return "outline_confirmed"
    return "outline_saved"


def _capture_stage_to_status(stage: str | None) -> str:
    normalized = str(stage or "").strip()
    if normalized == "generation_baseline":
        return "completed"
    if normalized == "outline_confirmed":
        return "ready_for_confirmation"
    return "draft"
