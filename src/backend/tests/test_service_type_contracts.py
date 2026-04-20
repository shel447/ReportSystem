import unittest
from typing import get_type_hints

from backend.contexts.conversation.application.models import ChatCommand, ChatResponse
from backend.contexts.conversation.application.services import ConversationService
from backend.contexts.conversation.infrastructure.models import (
    ConversationMessageAction,
    ConversationMessageContent,
    ConversationMessageMeta,
)
from backend.contexts.conversation.infrastructure.repositories import SqlAlchemyChatRepository
from backend.contexts.report_runtime.application.models import ReportAnswerView, ReportView
from backend.contexts.report_runtime.application.services import ReportRuntimeService
from backend.contexts.template_catalog.application.models import TemplateImportPreview
from backend.contexts.template_catalog.application.services import TemplateCatalogService
from backend.contexts.template_catalog.domain.models import ReportTemplate
from backend.contexts.template_catalog.infrastructure.repositories import SqlAlchemyTemplateCatalogRepository


class ServiceTypeContractTests(unittest.TestCase):
    def test_template_catalog_service_uses_formal_types(self):
        create_hints = get_type_hints(TemplateCatalogService.create_template)
        update_hints = get_type_hints(TemplateCatalogService.update_template)
        preview_hints = get_type_hints(TemplateCatalogService.preview_import_template)
        repository_create_hints = get_type_hints(SqlAlchemyTemplateCatalogRepository.create)

        self.assertIs(create_hints["payload"], ReportTemplate)
        self.assertIs(create_hints["return"], ReportTemplate)
        self.assertIs(update_hints["payload"], ReportTemplate)
        self.assertIs(update_hints["return"], ReportTemplate)
        self.assertIs(preview_hints["return"], TemplateImportPreview)
        self.assertIs(repository_create_hints["template"], ReportTemplate)
        self.assertIs(repository_create_hints["return"], ReportTemplate)

    def test_report_runtime_service_uses_formal_types(self):
        get_view_hints = get_type_hints(ReportRuntimeService.get_report_view)
        serialize_hints = get_type_hints(ReportRuntimeService.serialize_report_answer)

        self.assertIs(get_view_hints["return"], ReportView)
        self.assertIs(serialize_hints["return"], ReportAnswerView)

    def test_conversation_service_and_chat_repository_use_formal_types(self):
        send_hints = get_type_hints(ConversationService.send_message)
        append_hints = get_type_hints(SqlAlchemyChatRepository.append_message)

        self.assertIs(send_hints["data"], ChatCommand)
        self.assertIs(send_hints["return"], ChatResponse)
        self.assertIs(append_hints["content"], ConversationMessageContent)
        self.assertEqual(append_hints["action"], ConversationMessageAction | None)
        self.assertEqual(append_hints["meta"], ConversationMessageMeta | None)


if __name__ == "__main__":
    unittest.main()
