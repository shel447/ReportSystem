"""用于持久化权威报告模板定义的仓储适配器。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ....infrastructure.persistence.models import ReportTemplate as ReportTemplateRow
from ....shared.kernel.errors import ConflictError, NotFoundError
from ..domain.models import ReportTemplate, TemplateSummary, report_template_from_dict, report_template_to_dict
from .schema import validate_report_template


class SqlAlchemyTemplateCatalogRepository:
    """静态报告模板资源的持久化适配器。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, template: ReportTemplate) -> ReportTemplate:
        payload = report_template_to_dict(template)
        if self.exists(template.id):
            raise ConflictError("Template already exists")
        row = ReportTemplateRow(
            id=template.id,
            category=template.category,
            name=template.name,
            description=template.description,
            schema_version=template.schema_version,
            content=payload,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return _to_template(row)

    def update(self, template_id: str, template: ReportTemplate) -> ReportTemplate:
        payload = report_template_to_dict(template)
        row = self.db.get(ReportTemplateRow, template_id)
        if row is None:
            raise NotFoundError("Template not found")
        row.category = template.category
        row.name = template.name
        row.description = template.description
        row.schema_version = template.schema_version
        row.content = payload
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
    def validate(payload: dict) -> dict:
        # 通过网关承接结构校验，这样应用层可以替换校验实现而不影响业务规则。
        return validate_report_template(payload)


def _to_template(row: ReportTemplateRow) -> ReportTemplate:
    payload = dict(row.content or {})
    template = report_template_from_dict(payload)
    template.created_at = row.created_at
    template.updated_at = row.updated_at
    return template


def _to_summary(row: ReportTemplateRow) -> TemplateSummary:
    return TemplateSummary(
        id=row.id,
        category=row.category,
        name=row.name,
        description=row.description or "",
        schema_version=row.schema_version,
        updated_at=row.updated_at,
    )
