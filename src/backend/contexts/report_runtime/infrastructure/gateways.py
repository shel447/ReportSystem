from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..application.services import ReportDocumentService, ReportRuntimeService
from .repositories import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyGenerationBaselineRepository,
    SqlAlchemyReportInstanceRepository,
)
from ....shared.kernel.errors import UpstreamError, ValidationError
from ....ai_gateway import AIConfigurationError, AIRequestError, OpenAICompatGateway
from ....application.reporting.services import InstanceApplicationService, ScheduledRunApplicationService, is_v2_template
from ....domain.reporting.services import OutlineExpansionService
from ....document_service import (
    DocumentGenerationError,
    create_markdown_document,
    normalize_document_format,
    remove_document_file,
    resolve_document_absolute_path,
    serialize_document,
)
from ....infrastructure.reporting.repositories import (
    OpenAIContentGenerator,
    SqlAlchemyInstanceRepository,
    SqlAlchemyTemplateRepository,
)
from ....models import ReportTemplate as ReportTemplateModel
from ....report_generation_service import generate_single_section


class InstanceCreationGateway:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.service = build_legacy_instance_application_service(db)

    def create_instance(self, **kwargs):
        try:
            return self.service.create_instance(**kwargs)
        except AIConfigurationError as exc:
            raise ValidationError(str(exc)) from exc
        except AIRequestError as exc:
            raise UpstreamError(str(exc)) from exc


class ScheduledInstanceCreationGateway:
    def __init__(self, db: Session) -> None:
        self.db = db
        instance_repo = SqlAlchemyInstanceRepository(db)
        instance_service = build_legacy_instance_application_service(db)
        self.service = ScheduledRunApplicationService(
            instance_service=instance_service,
            instance_reader=instance_repo,
        )

    def create_instance_from_schedule(self, **kwargs):
        try:
            return self.service.create_instance_from_schedule(**kwargs)
        except AIConfigurationError as exc:
            raise ValidationError(str(exc)) from exc
        except AIRequestError as exc:
            raise UpstreamError(str(exc)) from exc


class RuntimeTemplateGateway:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_template_entity(self, template_id: str):
        return SqlAlchemyTemplateRepository(self.db).get_by_id(template_id)

    def get_runtime_template(self, template_id: str) -> dict[str, Any] | None:
        template = self.db.query(ReportTemplateModel).filter(ReportTemplateModel.template_id == template_id).first()
        if not template:
            return None
        return {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description or "",
            "report_type": template.report_type or "",
            "scenario": template.scenario or "",
            "match_keywords": template.match_keywords or [],
            "content_params": template.content_params or [],
            "outline": template.outline or [],
        }


class LegacySectionRuntimeGateway:
    def __init__(self, db: Session) -> None:
        self.db = db

    def regenerate_section(
        self,
        *,
        template_entity,
        template_record: dict[str, Any] | None,
        current_section: dict[str, Any],
        input_params: dict[str, Any],
        existing_sections: list[dict[str, Any]],
        section_index: int,
    ) -> dict[str, Any]:
        try:
            if template_entity and is_v2_template(template_entity):
                generator = OpenAIContentGenerator(self.db, gateway=OpenAICompatGateway())
                outline_node = ((current_section.get("debug") or {}).get("outline_node")) if isinstance(current_section, dict) else None
                if outline_node:
                    sections, _warnings = generator.generate_v2_from_outline(
                        template_entity,
                        [outline_node],
                        input_params or {},
                    )
                    if not sections:
                        raise ValidationError("Invalid section index")
                    return sections[0]
                sections, _warnings = generator.generate_v2(template_entity, input_params or {})
                if section_index >= len(sections):
                    raise ValidationError("Invalid section index")
                return sections[section_index]

            section_spec = {
                "title": current_section.get("title", "未命名章节"),
                "description": current_section.get("description", ""),
                "dynamic_meta": current_section.get("dynamic_meta"),
                "level": 1,
            }
            return generate_single_section(
                self.db,
                OpenAICompatGateway(),
                template_record or {},
                section_spec,
                input_params or {},
                existing_sections=existing_sections,
                section_index=section_index,
            )
        except AIConfigurationError as exc:
            raise ValidationError(str(exc)) from exc
        except AIRequestError as exc:
            raise UpstreamError(str(exc)) from exc


class ReportDocumentGateway:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, instance_id: str, format_name: str) -> dict[str, Any]:
        try:
            fmt = normalize_document_format(format_name)
            if fmt != "md":
                raise DocumentGenerationError("当前仅支持生成 Markdown 文档。")
            document = create_markdown_document(self.db, instance_id)
            return serialize_document(document)
        except DocumentGenerationError as exc:
            raise ValidationError(str(exc)) from exc

    def list(self, *, instance_id: str | None = None) -> list[dict[str, Any]]:
        import os

        repo = SqlAlchemyDocumentRepository(self.db)
        result: list[dict[str, Any]] = []
        for item in repo.list(instance_id=instance_id):
            try:
                absolute_path = resolve_document_absolute_path(item.file_path)
            except DocumentGenerationError:
                continue
            if not item.file_path or not os.path.exists(absolute_path):
                continue
            result.append(serialize_document(item))
        return result

    def get(self, document_id: str) -> dict[str, Any] | None:
        repo = SqlAlchemyDocumentRepository(self.db)
        row = repo.get(document_id)
        if not row:
            return None
        return serialize_document(row)

    def resolve_download(self, document_id: str) -> tuple[dict[str, Any] | None, str | None]:
        import os

        repo = SqlAlchemyDocumentRepository(self.db)
        row = repo.get(document_id)
        if not row:
            return None, None
        try:
            absolute_path = resolve_document_absolute_path(row.file_path)
        except DocumentGenerationError as exc:
            raise ValidationError(str(exc)) from exc
        if not absolute_path or not row.file_path or not os.path.exists(absolute_path):
            return serialize_document(row), None
        return serialize_document(row), absolute_path

    def delete(self, document_id: str) -> dict[str, Any] | None:
        repo = SqlAlchemyDocumentRepository(self.db)
        row = repo.get(document_id)
        if not row:
            return None
        remove_document_file(row)
        repo.delete(document_id)
        return {"message": "deleted"}


def build_report_runtime_service(db: Session) -> ReportRuntimeService:
    return ReportRuntimeService(
        instance_creator=InstanceCreationGateway(db),
        instance_repository=SqlAlchemyReportInstanceRepository(db),
        generation_baseline_repository=SqlAlchemyGenerationBaselineRepository(db),
        template_repository=RuntimeTemplateGateway(db),
        legacy_runtime=LegacySectionRuntimeGateway(db),
    )


def build_report_document_service(db: Session) -> ReportDocumentService:
    return ReportDocumentService(
        document_gateway=ReportDocumentGateway(db),
    )


def build_scheduled_instance_creator(db: Session) -> ScheduledInstanceCreationGateway:
    return ScheduledInstanceCreationGateway(db)


def build_legacy_instance_application_service(db: Session) -> InstanceApplicationService:
    template_repo = SqlAlchemyTemplateRepository(db)
    instance_repo = SqlAlchemyInstanceRepository(db)
    generator = OpenAIContentGenerator(db, gateway=OpenAICompatGateway())
    return InstanceApplicationService(
        template_reader=template_repo,
        instance_writer=instance_repo,
        content_generator=generator,
        outline_expansion_service=OutlineExpansionService(),
    )
