from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from ..ai_gateway import OpenAICompatGateway
from ..application.reporting.services import InstanceApplicationService, ScheduledRunApplicationService
from ..domain.reporting.services import OutlineExpansionService
from ..contexts.template_catalog.application.services import TemplateCatalogService
from ..contexts.template_catalog.infrastructure.repositories import (
    SqlAlchemyTemplateCatalogRepository,
    TemplateIndexGateway,
    TemplateSchemaGateway,
)
from ..contexts.report_runtime.application.services import ReportDocumentService, ReportRuntimeService
from ..contexts.report_runtime.infrastructure.adapters import (
    DocumentGatewayAdapter,
    InstanceCreatorAdapter,
    LegacySectionRuntimeAdapter,
    RuntimeTemplateAdapter,
    ScheduledInstanceCreatorAdapter,
)
from ..contexts.report_runtime.infrastructure.repositories import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyGenerationBaselineRepository,
    SqlAlchemyReportInstanceRepository,
)
from ..contexts.scheduling.application.services import SchedulingService
from ..contexts.scheduling.infrastructure.repositories import (
    SqlAlchemyScheduledTaskRepository,
    SqlAlchemyTaskExecutionRepository,
)
from ..contexts.conversation.application.services import ConversationService
from ..contexts.conversation.infrastructure.gateways import (
    ConversationCapabilityGateway,
    ConversationForkGateway,
    ConversationPersistenceGateway,
    ConversationReportGateway,
    ConversationStateGateway,
)
from .reporting.repositories import (
    OpenAIContentGenerator,
    SqlAlchemyInstanceRepository,
    SqlAlchemyTemplateRepository,
)


def build_instance_application_service(db: Session) -> InstanceApplicationService:
    template_repo = SqlAlchemyTemplateRepository(db)
    instance_repo = SqlAlchemyInstanceRepository(db)
    generator = OpenAIContentGenerator(db, gateway=OpenAICompatGateway())
    return InstanceApplicationService(
        template_reader=template_repo,
        instance_writer=instance_repo,
        content_generator=generator,
        outline_expansion_service=OutlineExpansionService(),
    )



def build_scheduled_run_application_service(db: Session) -> ScheduledRunApplicationService:
    instance_service = build_instance_application_service(db)
    instance_repo = SqlAlchemyInstanceRepository(db)
    return ScheduledRunApplicationService(
        instance_service=instance_service,
        instance_reader=instance_repo,
    )


class SystemClock:
    @staticmethod
    def now() -> datetime:
        return datetime.now()



def build_template_catalog_service(db: Session) -> TemplateCatalogService:
    return TemplateCatalogService(
        repository=SqlAlchemyTemplateCatalogRepository(db),
        matcher=TemplateIndexGateway(db),
        schema_gateway=TemplateSchemaGateway(),
    )



def build_report_runtime_service(db: Session) -> ReportRuntimeService:
    return ReportRuntimeService(
        instance_creator=InstanceCreatorAdapter(db),
        instance_repository=SqlAlchemyReportInstanceRepository(db),
        generation_baseline_repository=SqlAlchemyGenerationBaselineRepository(db),
        template_repository=RuntimeTemplateAdapter(db),
        content_generator=OpenAIContentGenerator(db, gateway=OpenAICompatGateway()),
        legacy_runtime=LegacySectionRuntimeAdapter(db),
    )



def build_report_document_service(db: Session) -> ReportDocumentService:
    return ReportDocumentService(
        document_gateway=DocumentGatewayAdapter(db),
        document_repository=SqlAlchemyDocumentRepository(db),
    )



def build_scheduling_service(db: Session) -> SchedulingService:
    return SchedulingService(
        task_repository=SqlAlchemyScheduledTaskRepository(db),
        execution_repository=SqlAlchemyTaskExecutionRepository(db),
        scheduled_instance_creator=ScheduledInstanceCreatorAdapter(db),
        document_service=build_report_document_service(db),
        clock=SystemClock(),
    )


def build_conversation_service(db: Session) -> ConversationService:
    return ConversationService(
        persistence=ConversationPersistenceGateway(db),
        state_gateway=ConversationStateGateway(),
        capability_gateway=ConversationCapabilityGateway(db),
        report_gateway=ConversationReportGateway(db),
        fork_gateway=ConversationForkGateway(db),
    )
