import unittest
from dataclasses import is_dataclass
from types import SimpleNamespace

from backend.contexts.report_runtime.application.services import ReportRuntimeService, build_report_dsl
from backend.contexts.report_runtime.domain.models import (
    CompositeTableComponent,
    ParameterConfirmation,
    ReportDsl,
    TemplateInstance,
    TemplateInstanceCatalog,
    TemplateInstancePresentationBlock,
    TemplateInstancePresentationDefinition,
    TemplateInstanceSection,
    TemplateInstanceSectionContent,
    TemplateInstanceCompositeTablePart,
    PartRuntimeContext,
    SectionRuntimeContext,
)
from backend.contexts.template_catalog.domain.models import OutlineDefinition, ReportTemplate, SummaryRowDef, SummaryTableSpec, CompositeTablePartLayout
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
        template=ReportTemplate(
            id="tpl_network_daily",
            category="network_operations",
            name="网络运行日报",
            description="面向网络运维中心的统一日报模板。",
            schema_version="template.v3",
        ),
        conversation_id="conv_001",
        chat_id="chat_001",
        status="ready_for_confirmation",
        capture_stage="confirm_params",
        revision=1,
        parameters=[],
        parameter_confirmation=ParameterConfirmation(missing_parameter_ids=[], confirmed=True),
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
            TemplateInstanceCatalog(
                id="catalog_overview",
                title="运行概览",
                rendered_title="运行概览",
                sections=[
                    TemplateInstanceSection(
                        id="section_overview",
                        outline=OutlineDefinition(
                            requirement="分析核心设备巡检信息。",
                            rendered_requirement="分析核心设备巡检信息。",
                            items=[],
                        ),
                        runtime_context=SectionRuntimeContext(bindings=[]),
                        content=TemplateInstanceSectionContent(
                            presentation=TemplateInstancePresentationDefinition(
                                kind="mixed",
                                blocks=[
                                    TemplateInstancePresentationBlock(
                                        id="block_device_inspection",
                                        type="composite_table",
                                        title="核心设备巡检信息",
                                        parts=[
                                            TemplateInstanceCompositeTablePart(
                                                id="part_basic_info",
                                                title="基础信息",
                                                source_type="query",
                                                dataset_id="dataset_device_basic",
                                                table_layout=CompositeTablePartLayout(kind="table", show_header=True),
                                                runtime_context=PartRuntimeContext(status="pending"),
                                            ),
                                            TemplateInstanceCompositeTablePart(
                                                id="part_inspection_summary",
                                                title="巡检问题及建议",
                                                source_type="summary",
                                                summary_spec=SummaryTableSpec(
                                                    part_ids=["part_basic_info"],
                                                    rows=[
                                                        SummaryRowDef(id="major_issue", title="主要问题"),
                                                        SummaryRowDef(id="action_advice", title="处理建议"),
                                                    ],
                                                ),
                                                runtime_context=PartRuntimeContext(status="pending"),
                                            ),
                                        ],
                                    )
                                ],
                            )
                        ),
                        skeleton_status="reusable",
                        user_edited=False,
                    )
                ],
            )
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
        self.assertTrue(is_dataclass(report))
        self.assertIsInstance(report, ReportDsl)
        components = report.catalogs[0].sections[0].components
        composite_table = next(component for component in components if isinstance(component, CompositeTableComponent))

        self.assertEqual(composite_table.id, "block_device_inspection")
        self.assertEqual(composite_table.data_properties.title, "核心设备巡检信息")
        self.assertEqual(len(composite_table.tables), 2)
        self.assertEqual(composite_table.tables[0].data_properties.source_id, "dataset_device_basic")
        self.assertEqual(composite_table.tables[1].data_properties.data[0]["title"], "主要问题")


if __name__ == "__main__":
    unittest.main()
