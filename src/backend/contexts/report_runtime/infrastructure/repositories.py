from __future__ import annotations

from copy import deepcopy
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from ..domain.models import GenerationBaseline, ReportInstance
from ...template_catalog.domain.models import ReportTemplate
from ....infrastructure.persistence.models import ReportDocument, ReportInstance as ReportInstanceModel, ReportTemplate as ReportTemplateModel, TemplateInstance, gen_id


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
    ) -> ReportInstance:
        row = ReportInstanceModel(
            instance_id=gen_id(),
            template_id=template_id,
            template_version=template_version,
            status=status,
            input_params=input_params,
            outline_content=outline_content,
            report_time=report_time,
            report_time_source=report_time_source,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return _to_instance(row)

    def get(self, instance_id: str) -> ReportInstance | None:
        row = self.db.query(ReportInstanceModel).filter(ReportInstanceModel.instance_id == instance_id).first()
        return _to_instance(row) if row else None

    def list(self, template_id: str | None = None) -> list[ReportInstance]:
        query = self.db.query(ReportInstanceModel)
        if template_id:
            query = query.filter(ReportInstanceModel.template_id == template_id)
        return [_to_instance(row) for row in query.order_by(ReportInstanceModel.created_at.desc()).all()]

    def update_fields(self, instance_id: str, updates: dict[str, Any]) -> ReportInstance:
        row = self.db.query(ReportInstanceModel).filter(ReportInstanceModel.instance_id == instance_id).first()
        if not row:
            raise LookupError("Instance not found")
        for key, value in updates.items():
            setattr(row, key, value)
        self.db.commit()
        self.db.refresh(row)
        return _to_instance(row)

    def replace_outline_section(self, instance_id: str, section_index: int, section_payload: dict[str, Any]) -> ReportInstance:
        row = self.db.query(ReportInstanceModel).filter(ReportInstanceModel.instance_id == instance_id).first()
        if not row:
            raise LookupError("Instance not found")
        content = list(row.outline_content or [])
        content[section_index] = section_payload
        row.outline_content = content
        flag_modified(row, "outline_content")
        self.db.commit()
        self.db.refresh(row)
        return _to_instance(row)

    def delete(self, instance_id: str) -> None:
        row = self.db.query(ReportInstanceModel).filter(ReportInstanceModel.instance_id == instance_id).first()
        if not row:
            raise LookupError("Instance not found")
        self.db.delete(row)
        self.db.commit()

    def get_input_params(self, instance_id: str) -> dict[str, Any] | None:
        row = self.db.query(ReportInstanceModel).filter(ReportInstanceModel.instance_id == instance_id).first()
        return deepcopy(row.input_params or {}) if row else None


class SqlAlchemyGenerationBaselineRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_instance(self, instance_id: str) -> GenerationBaseline | None:
        row = (
            self.db.query(TemplateInstance)
            .filter(TemplateInstance.report_instance_id == instance_id)
            .order_by(TemplateInstance.created_at.desc(), TemplateInstance.template_instance_id.desc())
            .first()
        )
        return _to_baseline(row) if row else None

    def list_map_by_instances(self, instance_ids: list[str]) -> dict[str, GenerationBaseline]:
        if not instance_ids:
            return {}
        rows = (
            self.db.query(TemplateInstance)
            .filter(TemplateInstance.report_instance_id.in_(instance_ids))
            .order_by(TemplateInstance.created_at.desc(), TemplateInstance.template_instance_id.desc())
            .all()
        )
        mapping: dict[str, GenerationBaseline] = {}
        for row in rows:
            if row.report_instance_id in mapping:
                continue
            mapping[row.report_instance_id] = _to_baseline(row)
        return mapping

    def delete_by_instance(self, instance_id: str) -> None:
        rows = self.db.query(TemplateInstance).filter(TemplateInstance.report_instance_id == instance_id).all()
        for row in rows:
            self.db.delete(row)
        self.db.commit()


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
        input_params=deepcopy(row.input_params or {}),
        outline_content=deepcopy(row.outline_content or []),
        report_time=row.report_time,
        report_time_source=row.report_time_source or "",
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_template(row: ReportTemplateModel) -> ReportTemplate:
    return ReportTemplate(
        template_id=row.template_id,
        name=row.name,
        description=row.description or "",
        report_type=row.report_type or "",
        scenario=row.scenario or "",
        template_type=row.template_type or "",
        scene=row.scene or "",
        match_keywords=list(row.match_keywords or []),
        content_params=list(row.content_params or []),
        parameters=list(row.parameters or []),
        outline=list(row.outline or []),
        sections=list(row.sections or []),
        schema_version=row.schema_version or "",
        output_formats=list(row.output_formats or []),
        version=row.version or "1.0",
        created_at=row.created_at,
    )


def _to_baseline(row: TemplateInstance) -> GenerationBaseline:
    return GenerationBaseline(
        template_instance_id=row.template_instance_id,
        template_id=row.template_id,
        template_name=row.template_name or row.template_id,
        session_id=row.session_id or "",
        capture_stage=row.capture_stage or "",
        input_params_snapshot=deepcopy(row.input_params_snapshot or {}),
        outline_snapshot=deepcopy(row.outline_snapshot or []),
        warnings=list(row.warnings or []),
        report_instance_id=row.report_instance_id,
        created_at=row.created_at,
    )
