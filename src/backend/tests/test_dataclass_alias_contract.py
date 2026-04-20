import unittest
from dataclasses import fields

from backend.contexts.report_runtime.domain.models import (
    ParameterConfirmation,
    ReportBasicInfo,
    ReportDsl,
    TemplateInstance,
    report_dsl_to_dict,
    template_instance_to_dict,
)
from backend.contexts.template_catalog.domain.models import (
    Parameter,
    ParameterRuntimeContext,
    ReportTemplate,
    report_template_to_dict,
)


def _alias_map(model_type: type) -> dict[str, str]:
    return {
        item.name: item.metadata.get("alias", item.name)
        for item in fields(model_type)
    }


class DataclassAliasContractTests(unittest.TestCase):
    def test_report_template_fields_define_public_camel_case_aliases(self):
        aliases = _alias_map(ReportTemplate)

        self.assertEqual("schemaVersion", aliases["schema_version"])
        self.assertEqual("createdAt", aliases["created_at"])
        self.assertEqual("updatedAt", aliases["updated_at"])

    def test_parameter_fields_define_public_camel_case_aliases(self):
        parameter_aliases = _alias_map(Parameter)
        runtime_aliases = _alias_map(ParameterRuntimeContext)

        self.assertEqual("inputType", parameter_aliases["input_type"])
        self.assertEqual("interactionMode", parameter_aliases["interaction_mode"])
        self.assertEqual("defaultValue", parameter_aliases["default_value"])
        self.assertEqual("runtimeContext", parameter_aliases["runtime_context"])
        self.assertEqual("valueSource", runtime_aliases["value_source"])
        self.assertEqual("queryContext", runtime_aliases["query_context"])

    def test_template_instance_and_report_dsl_fields_define_public_camel_case_aliases(self):
        template_instance_aliases = _alias_map(TemplateInstance)
        report_dsl_aliases = _alias_map(ReportDsl)
        report_basic_info_aliases = _alias_map(ReportBasicInfo)

        self.assertEqual("schemaVersion", template_instance_aliases["schema_version"])
        self.assertEqual("templateId", template_instance_aliases["template_id"])
        self.assertEqual("conversationId", template_instance_aliases["conversation_id"])
        self.assertEqual("chatId", template_instance_aliases["chat_id"])
        self.assertEqual("captureStage", template_instance_aliases["capture_stage"])
        self.assertEqual("parameterConfirmation", template_instance_aliases["parameter_confirmation"])
        self.assertEqual("basicInfo", report_dsl_aliases["basic_info"])
        self.assertEqual("reportMeta", report_dsl_aliases["report_meta"])
        self.assertEqual("schemaVersion", report_basic_info_aliases["schema_version"])
        self.assertEqual("subTitle", report_basic_info_aliases["sub_title"])
        self.assertEqual("templateId", report_basic_info_aliases["template_id"])

    def test_public_serializers_keep_lower_camel_case_contract(self):
        template = ReportTemplate(
            id="tpl_alias",
            category="ops",
            name="别名模板",
            description="验证小驼峰序列化。",
            schema_version="template.v3",
        )
        template_payload = report_template_to_dict(template)
        self.assertIn("schemaVersion", template_payload)
        self.assertNotIn("schema_version", template_payload)

        template_instance = TemplateInstance(
            id="ti_alias",
            schema_version="template-instance.vNext-draft",
            template_id="tpl_alias",
            template=template,
            conversation_id="conv_alias",
            chat_id="chat_alias",
            status="ready",
            capture_stage="confirm_params",
            revision=1,
            parameter_confirmation=ParameterConfirmation(),
        )
        instance_payload = template_instance_to_dict(template_instance)
        self.assertIn("templateId", instance_payload)
        self.assertIn("parameterConfirmation", instance_payload)
        self.assertNotIn("template_id", instance_payload)
        self.assertNotIn("parameter_confirmation", instance_payload)

        report_payload = report_dsl_to_dict(
            ReportDsl(
                basic_info=ReportBasicInfo(
                    id="rpt_alias",
                    schema_version="report.v1",
                    mode="report",
                    status="ready",
                )
            )
        )
        self.assertIn("basicInfo", report_payload)
        self.assertNotIn("basic_info", report_payload)


if __name__ == "__main__":
    unittest.main()
