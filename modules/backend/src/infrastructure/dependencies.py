from __future__ import annotations

from sqlalchemy.orm import Session

from ..contexts.conversation.application.services import ConversationService
from ..contexts.conversation.infrastructure.repositories import (
    SqlAlchemyChatRepository,
    SqlAlchemyConversationRepository,
)
from ..contexts.report.application.generation_services import ReportDocumentService, ReportGenerationService
from ..contexts.report.infrastructure.custom_content import CustomContentGateway
from ..contexts.report.infrastructure.documents import ReportDocumentGateway
from ..contexts.report.infrastructure.generation_repositories import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyExportJobRepository,
    SqlAlchemyReportInstanceRepository,
    SqlAlchemyRuntimeTemplateRepository,
    SqlAlchemyTemplateInstanceRepository,
)
from ..contexts.report.application.parameter_options import ParameterOptionService
from ..contexts.report.application.template_services import TemplateManagementService
from ..contexts.report.infrastructure.template_repositories import (
    SqlAlchemyTemplateManagementRepository,
    TemplateSchemaGateway,
)


def build_template_management_service(db: Session) -> TemplateManagementService:
    """装配报告模板管理应用服务及其依赖适配器。"""
    return TemplateManagementService(
        repository=SqlAlchemyTemplateManagementRepository(db),
        schema_gateway=TemplateSchemaGateway(),
    )


def build_parameter_option_service(db: Session | None = None) -> ParameterOptionService:
    """返回对话流和预览流共用的动态参数解析服务。"""
    return ParameterOptionService()


def build_report_generation_service(db: Session) -> ReportGenerationService:
    """围绕持久化与文档适配器装配报告生成服务。"""
    return ReportGenerationService(
        template_repository=SqlAlchemyRuntimeTemplateRepository(db),
        template_instance_repository=SqlAlchemyTemplateInstanceRepository(db),
        report_instance_repository=SqlAlchemyReportInstanceRepository(db),
        document_repository=SqlAlchemyDocumentRepository(db),
        export_job_repository=SqlAlchemyExportJobRepository(db),
        document_gateway=ReportDocumentGateway(),
        custom_content_gateway=CustomContentGateway(),
    )


def build_report_document_service(db: Session) -> ReportDocumentService:
    """暴露面向报告范围的文档下载门面。"""
    return ReportDocumentService(runtime_service=build_report_generation_service(db))


def build_conversation_service(db: Session) -> ConversationService:
    """装配聊天接口应用服务及其依赖上下文。"""
    return ConversationService(
        conversation_repository=SqlAlchemyConversationRepository(db),
        chat_repository=SqlAlchemyChatRepository(db),
        template_management_service=build_template_management_service(db),
        template_repository=SqlAlchemyTemplateManagementRepository(db),
        runtime_service=build_report_generation_service(db),
        parameter_option_service=build_parameter_option_service(db),
        db=db,
    )
