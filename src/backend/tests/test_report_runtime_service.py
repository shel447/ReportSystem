import unittest
from types import SimpleNamespace

from backend.contexts.report_runtime.application.services import ReportRuntimeService, build_report_dsl
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

    def test_generate_report_compiles_composite_table_block(self):
        service = _build_runtime_service()
        instance = _valid_template_instance()
        instance.catalogs = [
            {
                "id": "catalog_overview",
                "title": "运行概览",
                "renderedTitle": "运行概览",
                "sections": [
                    {
                        "id": "section_overview",
                        "outline": {
                            "requirement": "分析核心设备巡检信息。",
                            "renderedRequirement": "分析核心设备巡检信息。",
                            "items": [],
                        },
                        "runtimeContext": {"bindings": []},
                        "content": {
                            "presentation": {
                                "kind": "mixed",
                                "blocks": [
                                    {
                                        "id": "block_device_inspection",
                                        "type": "composite_table",
                                        "title": "核心设备巡检信息",
                                        "parts": [
                                            {
                                                "id": "part_basic_info",
                                                "title": "基础信息",
                                                "sourceType": "query",
                                                "datasetId": "dataset_device_basic",
                                                "tableLayout": {"kind": "table", "showHeader": True},
                                            },
                                            {
                                                "id": "part_inspection_summary",
                                                "title": "巡检问题及建议",
                                                "sourceType": "summary",
                                                "summarySpec": {
                                                    "partIds": ["part_basic_info"],
                                                    "rows": [
                                                        {"id": "major_issue", "title": "主要问题"},
                                                        {"id": "action_advice", "title": "处理建议"},
                                                    ],
                                                },
                                            },
                                        ],
                                    }
                                ],
                            }
                        },
                        "skeletonStatus": "reusable",
                        "userEdited": False,
                    }
                ],
            }
        ]

        report = build_report_dsl(
            report_id="rpt_001",
            template=SimpleNamespace(
                name="网络运行日报",
                description="面向网络运维中心的统一日报模板。",
                id="tpl_network_daily",
                category="network_ops",
            ),
            template_instance=instance,
        )
        components = report["catalogs"][0]["sections"][0]["components"]
        composite_table = next(component for component in components if component["type"] == "compositeTable")

        self.assertEqual(composite_table["id"], "block_device_inspection")
        self.assertEqual(composite_table["dataProperties"]["title"], "核心设备巡检信息")
        self.assertEqual(len(composite_table["tables"]), 2)
        self.assertEqual(composite_table["tables"][0]["dataProperties"]["sourceId"], "dataset_device_basic")
        self.assertEqual(composite_table["tables"][1]["dataProperties"]["data"][0]["title"], "主要问题")


if __name__ == "__main__":
    unittest.main()
