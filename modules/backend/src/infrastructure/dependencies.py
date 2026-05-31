from __future__ import annotations

from sqlalchemy.orm import Session

from ..contexts.conversation.application.services import ConversationService
from ..contexts.conversation.infrastructure.repositories import (
    SqlAlchemyChatRepository,
    SqlAlchemyConversationRepository,
)
from ..contexts.report.application.document_service import ReportDocumentService
from ..contexts.report.application.generation_service import ReportGenerationService
from ..contexts.report.application.report_service import ReportService
from ..contexts.report.application.scenario_service import ReportScenarioService
from ..contexts.report.infrastructure.custom_content import CustomContentGateway
from ..contexts.report.infrastructure.documents import ReportDocumentGateway
from ..contexts.report.infrastructure.generation_repositories import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyExportJobRepository,
    SqlAlchemyReportInstanceRepository,
    SqlAlchemyRuntimeTemplateRepository,
    SqlAlchemyTemplateInstanceRepository,
)
from ..contexts.report.application.parameter_service import ReportParameterService
from ..contexts.report.application.template_service import ReportTemplateService
from ..contexts.report.infrastructure.template_repositories import (
    SqlAlchemyTemplateManagementRepository,
    TemplateSchemaGateway,
)
from .ai.openai_compat import OpenAICompatGateway
from .settings.system_settings import build_embedding_provider_config


def _build_report_template_service(db: Session) -> ReportTemplateService:
    """装配报告模板管理应用服务及其依赖适配器。"""
    return ReportTemplateService(
        repository=SqlAlchemyTemplateManagementRepository(db),
        schema_gateway=TemplateSchemaGateway(),
    )


def _build_report_parameter_service(db: Session | None = None) -> ReportParameterService:
    """返回对话流和预览流共用的动态参数解析服务。"""
    return ReportParameterService()


def _build_report_generation_service(db: Session) -> ReportGenerationService:
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


def build_report_service(db: Session) -> ReportService:
    """装配 report context 的统一应用入口。"""
    template_service = _build_report_template_service(db)
    parameter_service = _build_report_parameter_service(db)
    generation_service = _build_report_generation_service(db)
    document_service = ReportDocumentService(generation_service=generation_service)
    scenario_service = ReportScenarioService(
        template_service=template_service,
        template_repository=SqlAlchemyTemplateManagementRepository(db),
        generation_service=generation_service,
        parameter_service=parameter_service,
        ai_gateway=OpenAICompatGateway(),
        embedding_config_builder=build_embedding_provider_config,
    )
    return ReportService(
        scenario_service=scenario_service,
        template_service=template_service,
        parameter_service=parameter_service,
        generation_service=generation_service,
        document_service=document_service,
    )


def build_conversation_service(db: Session) -> ConversationService:
    """装配聊天接口应用服务及其依赖上下文。"""
    return ConversationService(
        conversation_repository=SqlAlchemyConversationRepository(db),
        chat_repository=SqlAlchemyChatRepository(db),
        report_service=build_report_service(db),
    )
