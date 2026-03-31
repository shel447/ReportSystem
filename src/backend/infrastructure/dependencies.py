from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from ..contexts.template_catalog.application.services import TemplateCatalogService
from ..contexts.template_catalog.infrastructure.repositories import (
    SqlAlchemyTemplateCatalogRepository,
    TemplateIndexGateway,
    TemplateSchemaGateway,
)
from ..contexts.report_runtime.application.services import ReportDocumentService, ReportRuntimeService
from ..contexts.report_runtime.infrastructure.gateways import (
    build_report_document_service as build_report_document_service_for_context,
    build_report_runtime_service as build_report_runtime_service_for_context,
    build_scheduled_instance_creator,
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
    return build_report_runtime_service_for_context(db)



def build_report_document_service(db: Session) -> ReportDocumentService:
    return build_report_document_service_for_context(db)



def build_scheduling_service(db: Session) -> SchedulingService:
    return SchedulingService(
        task_repository=SqlAlchemyScheduledTaskRepository(db),
        execution_repository=SqlAlchemyTaskExecutionRepository(db),
        scheduled_instance_creator=build_scheduled_instance_creator(db),
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
