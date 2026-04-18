from __future__ import annotations

from sqlalchemy.orm import Session

from ..contexts.conversation.application.services import ConversationService
from ..contexts.conversation.infrastructure.repositories import (
    SqlAlchemyChatRepository,
    SqlAlchemyConversationRepository,
)
from ..contexts.report_runtime.application.services import ReportDocumentService, ReportRuntimeService
from ..contexts.report_runtime.infrastructure.documents import ReportDocumentGateway
from ..contexts.report_runtime.infrastructure.repositories import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyExportJobRepository,
    SqlAlchemyReportInstanceRepository,
    SqlAlchemyRuntimeTemplateRepository,
    SqlAlchemyTemplateInstanceRepository,
)
from ..contexts.template_catalog.application.parameter_options import ParameterOptionService
from ..contexts.template_catalog.application.services import TemplateCatalogService
from ..contexts.template_catalog.infrastructure.repositories import (
    SqlAlchemyTemplateCatalogRepository,
    TemplateSchemaGateway,
)


def build_template_catalog_service(db: Session) -> TemplateCatalogService:
    return TemplateCatalogService(
        repository=SqlAlchemyTemplateCatalogRepository(db),
        schema_gateway=TemplateSchemaGateway(),
    )


def build_parameter_option_service(db: Session | None = None) -> ParameterOptionService:
    return ParameterOptionService()


def build_report_runtime_service(db: Session) -> ReportRuntimeService:
    return ReportRuntimeService(
        template_repository=SqlAlchemyRuntimeTemplateRepository(db),
        template_instance_repository=SqlAlchemyTemplateInstanceRepository(db),
        report_instance_repository=SqlAlchemyReportInstanceRepository(db),
        document_repository=SqlAlchemyDocumentRepository(db),
        export_job_repository=SqlAlchemyExportJobRepository(db),
        document_gateway=ReportDocumentGateway(),
    )


def build_report_document_service(db: Session) -> ReportDocumentService:
    return ReportDocumentService(runtime_service=build_report_runtime_service(db))


def build_conversation_service(db: Session) -> ConversationService:
    return ConversationService(
        conversation_repository=SqlAlchemyConversationRepository(db),
        chat_repository=SqlAlchemyChatRepository(db),
        template_catalog_service=build_template_catalog_service(db),
        template_repository=SqlAlchemyTemplateCatalogRepository(db),
        runtime_service=build_report_runtime_service(db),
        parameter_option_service=build_parameter_option_service(db),
        db=db,
    )
