from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ...ai_gateway import OpenAICompatGateway
from ...application.reporting.ports import ContentGenerator, InstanceReader, InstanceWriter, TemplateReader
from ...domain.reporting.entities import ReportInstanceEntity, ReportTemplateEntity
from ...models import ReportInstance, ReportTemplate, gen_id
from ...report_generation_service import generate_report_sections
from ...section_query_service import generate_section_evidence
from ...system_settings_service import build_completion_provider_config
from ...template_v2_renderer import generate_report_sections_v2


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
            description=template.description or "",
            report_type=template.report_type or "",
            scenario=template.scenario or "",
            template_type=template.template_type or "",
            scene=template.scene or "",
            match_keywords=template.match_keywords or [],
            content_params=template.content_params or [],
            version=template.version,
            outline=template.outline or [],
            parameters=template.parameters or [],
            sections=template.sections or [],
            schema_version=template.schema_version or "",
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


class OpenAIContentGenerator(ContentGenerator):
    def __init__(self, db: Session, gateway: OpenAICompatGateway | None = None) -> None:
        self.db = db
        self.gateway = gateway or OpenAICompatGateway()

    def generate(
        self,
        template: ReportTemplateEntity,
        outline: List[Dict[str, Any]],
        params: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        return generate_report_sections(self.db, self.gateway, template, outline, params)

    def generate_v2(
        self,
        template: ReportTemplateEntity,
        params: Dict[str, Any],
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        config = build_completion_provider_config(self.db)
        template_context = {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "report_type": template.report_type,
            "scenario": template.scene or template.scenario,
        }

        def nl2sql_runner(*, description: str, params: Dict[str, Any], locals_ctx: Dict[str, Any], **_kwargs):
            section = {"title": "", "description": description}
            evidence = generate_section_evidence(
                gateway=self.gateway,
                config=config,
                template_context=template_context,
                section=section,
                params=params,
            )
            rows = evidence.get("debug", {}).get("sample_rows") or []
            columns = list(rows[0].keys()) if rows else []
            debug = evidence.get("debug") or {}
            return {"rows": rows, "columns": columns, "debug": debug}

        def ai_synthesis_runner(*, prompt: str, params: Dict[str, Any], locals_ctx: Dict[str, Any], **_kwargs):
            response = self.gateway.chat_completion(
                config,
                [
                    {"role": "system", "content": "你是报告撰写助手，负责基于上下文输出简洁的中文总结。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=config.temperature,
                max_tokens=600,
            )
            return response["content"]

        return generate_report_sections_v2(
            {
                "name": template.name,
                "sections": template.sections or [],
            },
            params,
            nl2sql_runner=nl2sql_runner,
            ai_synthesis_runner=ai_synthesis_runner,
        )
