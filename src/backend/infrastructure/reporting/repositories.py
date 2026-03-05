from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ...application.reporting.ports import ContentGenerator, InstanceReader, InstanceWriter, TemplateReader
from ...domain.reporting.entities import ReportInstanceEntity, ReportTemplateEntity
from ...llm_mock import generate_report_content
from ...models import ReportInstance, ReportTemplate, gen_id


class SqlAlchemyTemplateRepository(TemplateReader):
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, template_id: str) -> ReportTemplateEntity | None:
        template = self.db.query(ReportTemplate).filter(ReportTemplate.template_id == template_id).first()
        if not template:
            return None
        return ReportTemplateEntity(
            template_id=template.template_id,
            name=template.name,
            version=template.version,
            outline=template.outline or [],
        )


class SqlAlchemyInstanceRepository(InstanceWriter, InstanceReader):
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        template_id: str,
        template_version: str,
        input_params: Dict[str, Any],
        outline_content: List[Dict[str, Any]],
        status: str = "draft",
    ) -> ReportInstanceEntity:
        instance = ReportInstance(
            instance_id=gen_id(),
            template_id=template_id,
            template_version=template_version,
            status=status,
            input_params=input_params,
            outline_content=outline_content,
        )
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return ReportInstanceEntity(
            instance_id=instance.instance_id,
            template_id=instance.template_id,
            template_version=instance.template_version,
            status=instance.status,
            input_params=instance.input_params or {},
            outline_content=instance.outline_content or [],
            created_at=instance.created_at,
            updated_at=instance.updated_at,
        )

    def get_input_params(self, instance_id: str) -> Dict[str, Any] | None:
        instance = self.db.query(ReportInstance).filter(ReportInstance.instance_id == instance_id).first()
        if not instance:
            return None
        return instance.input_params or {}


class MockContentGenerator(ContentGenerator):
    def generate(
        self,
        template_name: str,
        outline: List[Dict[str, Any]],
        params: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        return generate_report_content(template_name, outline, params)
