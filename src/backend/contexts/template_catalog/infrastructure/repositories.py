from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ....infrastructure.persistence.models import ReportTemplate as ReportTemplateRow
from ....shared.kernel.errors import ConflictError, NotFoundError
from ..domain.models import ReportTemplate, TemplateSummary
from .schema import validate_report_template


class SqlAlchemyTemplateCatalogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, template: dict[str, Any]) -> ReportTemplate:
        if self.exists(template["id"]):
            raise ConflictError("Template already exists")
        row = ReportTemplateRow(
            id=template["id"],
            category=template["category"],
            name=template["name"],
            description=template["description"],
            schema_version=template["schemaVersion"],
            content=template,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return _to_template(row)

    def update(self, template_id: str, template: dict[str, Any]) -> ReportTemplate:
        row = self.db.get(ReportTemplateRow, template_id)
        if row is None:
            raise NotFoundError("Template not found")
        row.category = template["category"]
        row.name = template["name"]
        row.description = template["description"]
        row.schema_version = template["schemaVersion"]
        row.content = template
        self.db.commit()
        self.db.refresh(row)
        return _to_template(row)

    def delete(self, template_id: str) -> None:
        row = self.db.get(ReportTemplateRow, template_id)
        if row is None:
            raise NotFoundError("Template not found")
        self.db.delete(row)
        self.db.commit()

    def get(self, template_id: str) -> ReportTemplate | None:
        row = self.db.get(ReportTemplateRow, template_id)
        return _to_template(row) if row else None

    def list_all(self) -> list[ReportTemplate]:
        rows = self.db.query(ReportTemplateRow).order_by(ReportTemplateRow.updated_at.desc()).all()
        return [_to_template(row) for row in rows]

    def list_summaries(self) -> list[TemplateSummary]:
        return [_to_summary(row) for row in self.db.query(ReportTemplateRow).order_by(ReportTemplateRow.updated_at.desc()).all()]

    def exists(self, template_id: str) -> bool:
        return self.db.get(ReportTemplateRow, template_id) is not None


class TemplateSchemaGateway:
    @staticmethod
    def validate(payload: dict[str, Any]) -> dict[str, Any]:
        return validate_report_template(payload)


def _to_template(row: ReportTemplateRow) -> ReportTemplate:
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


def _to_summary(row: ReportTemplateRow) -> TemplateSummary:
    return TemplateSummary(
        id=row.id,
        category=row.category,
        name=row.name,
        description=row.description or "",
        schema_version=row.schema_version,
        updated_at=row.updated_at,
    )
