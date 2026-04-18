import unittest
from types import SimpleNamespace

from backend.contexts.report_runtime.application.services import ReportRuntimeService
from backend.contexts.report_runtime.domain.models import TemplateInstance
from backend.shared.kernel.errors import ValidationError


def _build_runtime_service():
    return ReportRuntimeService(
        template_repository=SimpleNamespace(),
        template_instance_repository=SimpleNamespace(
            get=lambda instance_id, user_id: None,
            create=lambda instance, user_id: instance,
            update=lambda instance, user_id: instance,
        ),
        report_instance_repository=SimpleNamespace(),
        document_repository=SimpleNamespace(list_by_report=lambda report_id: []),
        export_job_repository=SimpleNamespace(),
        document_gateway=SimpleNamespace(),
    )


def _valid_template_instance():
    return TemplateInstance(
        id="ti_001",
        schema_version="template-instance.vNext-draft",
        template_id="tpl_network_daily",
        template={
            "id": "tpl_network_daily",
            "category": "network_operations",
            "name": "网络运行日报",
            "description": "面向网络运维中心的统一日报模板。",
            "schemaVersion": "template.v3",
            "parameters": [],
            "catalogs": [],
        },
        conversation_id="conv_001",
        chat_id="chat_001",
        status="ready_for_confirmation",
        capture_stage="confirm_params",
        revision=1,
        parameters=[],
        parameter_confirmation={"missingParameterIds": [], "confirmed": True},
        catalogs=[],
        warnings=[],
    )


class ReportRuntimeServiceTests(unittest.TestCase):
    def test_persist_template_instance_validates_formal_schema(self):
        service = _build_runtime_service()
        instance = _valid_template_instance()
        instance.status = "not_a_valid_status"

        with self.assertRaises(ValidationError) as ctx:
            service.persist_template_instance(instance, user_id="default")

        self.assertIn("模板实例校验失败", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
