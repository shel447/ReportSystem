import unittest
from typing import get_type_hints

from src.contexts.conversation.application.models import ChatCommand, ChatResponse
from src.contexts.conversation.application.services import ConversationService
from src.contexts.conversation.infrastructure.models import (
    ConversationMessageAction,
    ConversationMessageContent,
    ConversationMessageMeta,
)
from src.contexts.conversation.infrastructure.repositories import SqlAlchemyChatRepository
from src.contexts.report.application.generation_models import ReportAnswerView, ReportView
from src.contexts.report.application.generation_service import ReportGenerationService
from src.contexts.report.application.report_service import ReportService
from src.contexts.report.application.template_models import TemplateImportPreview
from src.contexts.report.application.template_service import ReportTemplateService
from src.contexts.report.domain.template_models import ReportTemplate
from src.contexts.report.infrastructure.template_repositories import SqlAlchemyTemplateManagementRepository


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

    def test_conversation_service_and_chat_repository_use_formal_types(self):
        chat_hints = get_type_hints(ConversationService.chat)
        append_hints = get_type_hints(SqlAlchemyChatRepository.append_message)

        self.assertIs(chat_hints["data"], ChatCommand)
        self.assertIs(chat_hints["return"], ChatResponse)
        self.assertIs(append_hints["content"], ConversationMessageContent)
        self.assertEqual(append_hints["action"], ConversationMessageAction | None)
        self.assertEqual(append_hints["meta"], ConversationMessageMeta | None)


if __name__ == "__main__":
    unittest.main()
