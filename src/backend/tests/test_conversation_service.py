import unittest
from types import SimpleNamespace

from backend.contexts.conversation.application.services import ConversationService, _missing_required_parameters
from backend.contexts.report_runtime.domain.services import instantiate_template_instance


def _service():
    return ConversationService(
        conversation_repository=SimpleNamespace(),
        chat_repository=SimpleNamespace(),
        template_catalog_service=SimpleNamespace(),
        template_repository=SimpleNamespace(),
        runtime_service=SimpleNamespace(),
        parameter_option_service=SimpleNamespace(resolve=lambda **kwargs: {"options": []}),
        db=None,
    )


def _scoped_template():
    return {
        "id": "tpl_scoped",
        "category": "network_operations",
        "name": "作用域参数模板",
        "description": "验证目录和章节级参数。",
        "schemaVersion": "template.v3",
        "parameters": [],
        "catalogs": [
            {
                "id": "catalog_overview",
                "title": "运行概览",
                "sections": [
                    {
                        "id": "section_scope",
                        "parameters": [
                            {
                                "id": "scope",
                                "label": "分析对象",
                                "inputType": "free_text",
                                "required": True,
                                "multi": True,
                                "interactionMode": "form",
                            }
                        ],
                        "outline": {
                            "requirement": "分析{$scope.display}的总体运行态势。",
                            "items": [],
                        },
                        "content": {
                            "datasets": [],
                            "presentation": {"kind": "mixed", "blocks": []},
                        },
                    }
                ],
            }
        ],
    }


class ConversationServiceScopedParameterTests(unittest.TestCase):
    def test_extract_parameter_values_reads_section_scoped_parameters(self):
        service = _service()

        values = service._extract_parameter_values(_scoped_template(), "请分析华东、华北的运行态势")

        self.assertIn("scope", values)
        self.assertEqual(values["scope"][0]["display"], "请分析华东、华北的运行态势")

    def test_missing_required_parameters_includes_section_scoped_parameters(self):
        template = _scoped_template()
        instance = instantiate_template_instance(
            instance_id="ti_001",
            template=template,
            conversation_id="conv_001",
            chat_id="chat_001",
            status="collecting_parameters",
            capture_stage="fill_params",
            revision=1,
            parameter_values={},
        )

        missing = _missing_required_parameters(template=template, template_instance={
            "parameters": instance.parameters,
            "catalogs": instance.catalogs,
        })

        self.assertEqual([item["id"] for item in missing], ["scope"])


if __name__ == "__main__":
    unittest.main()
