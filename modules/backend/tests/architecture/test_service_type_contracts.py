import unittest
from typing import get_type_hints

from src.contexts.conversation.application.models import ChatCommand, ChatResponse
from src.contexts.conversation.application.services import ConversationService
from src.contexts.conversation.application.ports import ConversationHistoryGateway, HostedChat
from src.contexts.conversation.infrastructure.agentcore import ExternalConversationHistoryGateway
from src.contexts.conversation.application.scenarios import ScenarioCodec, ScenarioHandler, ScenarioRegistrationProvider
from src.contexts.data_analysis.application.ports import ApiDatasetGateway, DataCatalogGateway, KnowledgeGateway, LogicalEntityValidator, Nl2SqlCompiler, OneQueryGateway
from src.contexts.data_analysis.infrastructure.gateways import (
    ExternalApiDatasetGateway,
    ExternalDataCatalogGateway,
    ExternalKnowledgeGateway,
    ExternalOneQueryGateway,
)
from src.contexts.data_analysis.infrastructure.nl2sql_compiler import RestrictedIbisNl2SqlCompiler
from src.contexts.data_analysis.infrastructure.logical_entity_validator import DataCatalogLogicalEntityValidator
from src.contexts.data_analysis.infrastructure.scenario_registration import DataAnalysisScenarioCodec, DataAnalysisScenarioHandler, DataAnalysisScenarioRegistrationProvider
from src.contexts.report.application.generation_models import ReportAnswerView, ReportView
from src.contexts.report.application.interfaces import DocumentExportGateway, ParameterOptionsResolver, ReportSchemaValidator
from src.contexts.report.application.generation_service import ReportGenerationService
from src.contexts.report.application.report_service import ReportService
from src.contexts.report.application.template_models import TemplateImportPreview
from src.contexts.report.application.template_service import ReportTemplateService
from src.contexts.report.domain.template_models import ReportTemplate
from src.contexts.report.infrastructure.documents import ReportDocumentGateway
from src.contexts.report.infrastructure.parameter_options import ParameterOptionsGateway
from src.contexts.report.infrastructure.scenario_registration import ReportScenarioCodec, ReportScenarioHandler, ReportScenarioRegistrationProvider
from src.contexts.report.infrastructure.template_schema import ReportDslSchemaGateway
from src.contexts.report.infrastructure.template_repositories import SqlAlchemyTemplateManagementRepository
from src.infrastructure.platform.guardrail import ExternalGuardrailGateway
from src.infrastructure.platform.audit import AuditEventPublisher
from src.infrastructure.configuration.sources import (
    DatabaseConfigSource,
    EnvironmentConfigSource,
    NodeAgentAppConfigSource,
    RuntimeIniConfigSource,
)
from src.shared.configuration import ConfigSource
from src.shared.agentflow.checkpoints import CheckpointSaver, InMemoryCheckpointSaver
from src.shared.kernel.audit import AuditPublisher
from src.shared.kernel.safety import GuardrailGateway


class ServiceTypeContractTests(unittest.TestCase):
    def test_template_management_service_uses_formal_types(self):
        create_hints = get_type_hints(ReportTemplateService.create_template)
        update_hints = get_type_hints(ReportTemplateService.update_template)
        preview_hints = get_type_hints(ReportTemplateService.preview_import_template)
        repository_create_hints = get_type_hints(SqlAlchemyTemplateManagementRepository.create)

        self.assertIs(create_hints["payload"], ReportTemplate)
        self.assertIs(create_hints["return"], ReportTemplate)
        self.assertIs(update_hints["payload"], ReportTemplate)
        self.assertIs(update_hints["return"], ReportTemplate)
        self.assertIs(preview_hints["return"], TemplateImportPreview)
        self.assertIs(repository_create_hints["template"], ReportTemplate)
        self.assertIs(repository_create_hints["return"], ReportTemplate)

    def test_report_generation_service_uses_formal_types(self):
        get_view_hints = get_type_hints(ReportGenerationService.get_report_view)
        serialize_hints = get_type_hints(ReportGenerationService.serialize_report_answer)

        self.assertIs(get_view_hints["return"], ReportView)
        self.assertIs(serialize_hints["return"], ReportAnswerView)

    def test_report_service_exposes_formal_report_view(self):
        get_view_hints = get_type_hints(ReportService.get_report_view)

        self.assertIs(get_view_hints["return"], ReportView)

    def test_conversation_service_and_agentcore_gateway_use_formal_types(self):
        chat_hints = get_type_hints(ConversationService.chat)
        import_hints = get_type_hints(ExternalConversationHistoryGateway.import_chat)

        self.assertIs(chat_hints["data"], ChatCommand)
        self.assertIs(chat_hints["return"], ChatResponse)
        self.assertIs(import_hints["chat"], HostedChat)

    def test_infrastructure_adapters_explicitly_inherit_owned_protocols(self):
        pairs = [
            (ExternalConversationHistoryGateway, ConversationHistoryGateway),
            (ExternalGuardrailGateway, GuardrailGateway),
            (ExternalOneQueryGateway, OneQueryGateway),
            (ExternalApiDatasetGateway, ApiDatasetGateway),
            (ExternalDataCatalogGateway, DataCatalogGateway),
            (ExternalKnowledgeGateway, KnowledgeGateway),
            (RestrictedIbisNl2SqlCompiler, Nl2SqlCompiler),
            (DataCatalogLogicalEntityValidator, LogicalEntityValidator),
            (ReportScenarioCodec, ScenarioCodec),
            (ReportScenarioHandler, ScenarioHandler),
            (ReportScenarioRegistrationProvider, ScenarioRegistrationProvider),
            (DataAnalysisScenarioCodec, ScenarioCodec),
            (DataAnalysisScenarioHandler, ScenarioHandler),
            (DataAnalysisScenarioRegistrationProvider, ScenarioRegistrationProvider),
            (ParameterOptionsGateway, ParameterOptionsResolver),
            (ReportDslSchemaGateway, ReportSchemaValidator),
            (ReportDocumentGateway, DocumentExportGateway),
            (InMemoryCheckpointSaver, CheckpointSaver),
            (AuditEventPublisher, AuditPublisher),
            (RuntimeIniConfigSource, ConfigSource),
            (NodeAgentAppConfigSource, ConfigSource),
            (DatabaseConfigSource, ConfigSource),
            (EnvironmentConfigSource, ConfigSource),
        ]

        for implementation, protocol in pairs:
            with self.subTest(implementation=implementation.__name__, protocol=protocol.__name__):
                self.assertIn(protocol, implementation.__mro__)


if __name__ == "__main__":
    unittest.main()
