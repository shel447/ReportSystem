"""Composition builder for the report context."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ....infrastructure.ai.openai_compat import OpenAICompatGateway
from ....infrastructure.configuration import build_completion_provider_config, build_embedding_provider_config
from ....infrastructure.prompts import get_prompt_catalog
from ....infrastructure.platform.client import RuntimeHttpClient
from ....infrastructure.platform.runtime import build_runtime_client
from ....shared.messaging import MessagePublisher
from ..application.custom_content_resolver import CustomContentResolver
from ..application.dataset_execution_service import DatasetExecutionService
from ..application.document_service import ReportDocumentService
from ..application.generation_service import ReportGenerationService
from ..application.parameter_service import ReportParameterService
from ..application.report_service import ReportService
from ..application.scenario_service import ReportScenarioService
from ..application.template_service import ReportTemplateService
from ..domain.report_dsl_compiler import ReportDslCompiler
from .custom_content import CustomContentGateway
from .documents import ReportDocumentGateway
from .external_business import ExternalBusinessGateway
from .generation_repositories import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyExportJobRepository,
    SqlAlchemyReportInstanceRepository,
    SqlAlchemyRuntimeTemplateRepository,
    SqlAlchemyTemplateInstanceRepository,
)
from .parameter_options import ParameterOptionsGateway
from .scenario_registration import ReportScenarioRegistrationProvider
from .template_repositories import SqlAlchemyTemplateManagementRepository, TemplateSchemaGateway
from .template_schema import ReportDslSchemaGateway


def _client() -> RuntimeHttpClient:
    return build_runtime_client()


def build_report_service(db: Session, *, dataset_query_gateway=None, message_publisher: MessagePublisher | None = None) -> ReportService:
    template_service = ReportTemplateService(
        repository=SqlAlchemyTemplateManagementRepository(db),
        schema_gateway=TemplateSchemaGateway(),
    )
    external_gateway = ExternalBusinessGateway(client=_client())
    parameter_service = ReportParameterService(
        options_gateway=ParameterOptionsGateway(gateway=external_gateway),
        ai_gateway=OpenAICompatGateway(),
        completion_config_builder=build_completion_provider_config,
        prompt_catalog=get_prompt_catalog(),
    )
    schema_gateway = ReportDslSchemaGateway()
    generation_service = ReportGenerationService(
        template_repository=SqlAlchemyRuntimeTemplateRepository(db),
        template_instance_repository=SqlAlchemyTemplateInstanceRepository(db),
        report_instance_repository=SqlAlchemyReportInstanceRepository(db),
        compiler=ReportDslCompiler(),
        custom_content_resolver=CustomContentResolver(
            gateway=CustomContentGateway(gateway=external_gateway),
            schema_gateway=schema_gateway,
        ),
        dataset_execution_service=DatasetExecutionService(
            query_service=dataset_query_gateway,
            schema_gateway=schema_gateway,
        ) if dataset_query_gateway is not None else None,
        schema_gateway=schema_gateway,
        message_publisher=message_publisher,
    )
    document_service = ReportDocumentService(
        report_reader=generation_service,
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


def build_report_scenario_provider(db: Session, *, dataset_query_gateway=None, message_publisher: MessagePublisher | None = None) -> ReportScenarioRegistrationProvider:
    return ReportScenarioRegistrationProvider(
        report_service=build_report_service(
            db,
            dataset_query_gateway=dataset_query_gateway,
            message_publisher=message_publisher,
        )
    )
