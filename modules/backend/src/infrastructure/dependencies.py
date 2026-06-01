from __future__ import annotations

from sqlalchemy.orm import Session

from ..contexts.conversation.application.services import ConversationService
from ..contexts.conversation.application.scenarios import ScenarioDispatchService, ScenarioRegistry
from ..contexts.conversation.infrastructure.agentcore import ExternalConversationHistoryGateway
from ..contexts.conversation.infrastructure.guardrail import ExternalGuardrailGateway
from ..contexts.data_analysis.application.services import DataAnalysisService, DataQueryService
from ..contexts.data_analysis.infrastructure.gateways import (
    ExternalApiDatasetGateway,
    ExternalDataCatalogGateway,
    ExternalKnowledgeGateway,
    ExternalOneQueryGateway,
)
from ..contexts.report.application.document_service import ReportDocumentService
from ..contexts.report.application.custom_content_resolver import CustomContentResolver
from ..contexts.report.application.dataset_execution_service import DatasetExecutionService
from ..contexts.report.application.generation_service import ReportGenerationService
from ..contexts.report.application.report_service import ReportService
from ..contexts.report.application.scenario_service import ReportScenarioService
from ..contexts.report.infrastructure.custom_content import CustomContentGateway
from ..contexts.report.infrastructure.external_business import ExternalBusinessGateway
from ..contexts.report.infrastructure.parameter_options import ParameterOptionsGateway
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
from ..contexts.report.infrastructure.template_schema import ReportDslSchemaGateway
from ..contexts.report.domain.report_dsl_compiler import ReportDslCompiler
from .ai.openai_compat import OpenAICompatGateway
from .platform.http_client import PlatformHttpClient
from .platform.runtime import audit_dispatcher, build_platform_client
from .settings.system_settings import build_completion_provider_config, build_embedding_provider_config
from .scenarios.report_conversation import report_scenario_registration
from .scenarios.data_analysis_conversation import data_analysis_scenario_registration
def _build_platform_client(*, service_key: str | None = None) -> PlatformHttpClient:
    return build_platform_client(service_key=service_key)


def _build_guardrail_gateway():
    return ExternalGuardrailGateway(client=_build_platform_client(service_key="guardrail"))


def _build_data_query_service() -> DataQueryService:
    client = _build_platform_client(service_key="query")
    return DataQueryService(
        onequery_gateway=ExternalOneQueryGateway(client=client),
        api_gateway=ExternalApiDatasetGateway(client=client),
    )


def _build_data_analysis_service() -> DataAnalysisService:
    client = _build_platform_client(service_key="analysis")
    return DataAnalysisService(
        query_service=_build_data_query_service(),
        data_catalog_gateway=ExternalDataCatalogGateway(client=client),
        knowledge_gateway=ExternalKnowledgeGateway(client=client),
        guardrail_gateway=_build_guardrail_gateway(),
        ai_gateway=OpenAICompatGateway(),
        completion_config_builder=build_completion_provider_config,
        audit_dispatcher=audit_dispatcher,
    )


def _build_report_template_service(db: Session) -> ReportTemplateService:
    """装配报告模板管理应用服务及其依赖适配器。"""
    return ReportTemplateService(
        repository=SqlAlchemyTemplateManagementRepository(db),
        schema_gateway=TemplateSchemaGateway(),
    )


def _build_report_parameter_service(db: Session | None = None) -> ReportParameterService:
    """返回对话流和预览流共用的动态参数解析服务。"""
    external_gateway = ExternalBusinessGateway(client=_build_platform_client(service_key="external_business"))
    return ReportParameterService(options_gateway=ParameterOptionsGateway(gateway=external_gateway))


def _build_report_generation_service(db: Session) -> ReportGenerationService:
    """围绕模板实例、报告仓储和纯领域 compiler 装配报告生成服务。"""
    schema_gateway = ReportDslSchemaGateway()
    external_gateway = ExternalBusinessGateway(client=_build_platform_client(service_key="external_business"))
    return ReportGenerationService(
        template_repository=SqlAlchemyRuntimeTemplateRepository(db),
        template_instance_repository=SqlAlchemyTemplateInstanceRepository(db),
        report_instance_repository=SqlAlchemyReportInstanceRepository(db),
        compiler=ReportDslCompiler(),
        custom_content_resolver=CustomContentResolver(
            gateway=CustomContentGateway(gateway=external_gateway),
            schema_gateway=schema_gateway,
        ),
        dataset_execution_service=DatasetExecutionService(query_service=_build_data_query_service(), schema_gateway=schema_gateway),
        schema_gateway=schema_gateway,
    )


def build_report_service(db: Session) -> ReportService:
    """装配 report context 的统一应用入口。"""
    template_service = _build_report_template_service(db)
    parameter_service = _build_report_parameter_service(db)
    generation_service = _build_report_generation_service(db)
    document_service = ReportDocumentService(
        generation_service=generation_service,
        document_repository=SqlAlchemyDocumentRepository(db),
        export_job_repository=SqlAlchemyExportJobRepository(db),
        document_gateway=ReportDocumentGateway(),
    )
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
    registry = ScenarioRegistry()
    registry.register(report_scenario_registration(report_service=build_report_service(db)))
    registry.register(data_analysis_scenario_registration(service=_build_data_analysis_service()))
    registry.seal()
    return ConversationService(
        history_gateway=ExternalConversationHistoryGateway(client=_build_platform_client(service_key="agentcore")),
        guardrail_gateway=_build_guardrail_gateway(),
        scenario_dispatcher=ScenarioDispatchService(registry=registry),
        audit_dispatcher=audit_dispatcher,
    )
