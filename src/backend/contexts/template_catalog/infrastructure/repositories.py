from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..domain.models import ReportTemplate
from ....shared.kernel.errors import NotFoundError
from ....infrastructure.persistence.models import ReportTemplate as ReportTemplateModel, gen_id
from .indexing import delete_template_index, mark_template_index_stale, match_templates
from .schema import validate_template_payload


class SqlAlchemyTemplateCatalogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: dict[str, Any]) -> ReportTemplate:
        row = ReportTemplateModel(template_id=gen_id(), **payload)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return _to_domain(row)

    def list_all(self) -> list[ReportTemplate]:
        return [_to_domain(row) for row in self.db.query(ReportTemplateModel).all()]

    def get(self, template_id: str) -> ReportTemplate | None:
        row = self.db.query(ReportTemplateModel).filter(ReportTemplateModel.template_id == template_id).first()
        return _to_domain(row) if row else None

    def update(self, template_id: str, payload: dict[str, Any]) -> ReportTemplate:
        row = self.db.query(ReportTemplateModel).filter(ReportTemplateModel.template_id == template_id).first()
        if not row:
            raise NotFoundError("Template not found")
        for key, value in payload.items():
            setattr(row, key, value)
        self.db.commit()
        self.db.refresh(row)
        return _to_domain(row)

    def delete(self, template_id: str) -> None:
        row = self.db.query(ReportTemplateModel).filter(ReportTemplateModel.template_id == template_id).first()
        if not row:
            raise NotFoundError("Template not found")
        self.db.delete(row)
        self.db.commit()


class TemplateSchemaGateway:
    @staticmethod
    def validate(payload: dict[str, Any]) -> dict[str, Any]:
        return validate_template_payload(payload)


class TemplateIndexGateway:
    def __init__(self, db: Session) -> None:
        self.db = db

    def mark_stale(self, template_id: str, reason: str) -> None:
        mark_template_index_stale(self.db, template_id, reason)

    def delete_index(self, template_id: str) -> None:
        delete_template_index(self.db, template_id)

    def match(self, message: str, gateway) -> dict[str, Any]:
        return match_templates(self.db, message, gateway)


def _to_domain(row: ReportTemplateModel) -> ReportTemplate:
    return ReportTemplate(
        template_id=row.template_id,
        name=row.name,
        description=getattr(row, "description", "") or "",
        report_type=getattr(row, "report_type", "") or "",
        scenario=getattr(row, "scenario", "") or "",
        template_type=getattr(row, "template_type", "") or "",
        scene=getattr(row, "scene", "") or "",
        match_keywords=list(getattr(row, "match_keywords", []) or []),
        content_params=list(getattr(row, "content_params", []) or []),
        parameters=list(getattr(row, "parameters", []) or []),
        outline=list(getattr(row, "outline", []) or []),
        sections=list(getattr(row, "sections", []) or []),
        schema_version=getattr(row, "schema_version", "") or "",
        output_formats=list(getattr(row, "output_formats", []) or []),
        version=getattr(row, "version", "1.0") or "1.0",
        created_at=getattr(row, "created_at", None),
    )
