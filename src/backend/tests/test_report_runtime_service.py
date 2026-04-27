import copy
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
    TableComponent,
    TableDataProperties,
    table_component_from_dict,
    table_component_to_dict,
)
from backend.contexts.template_catalog.domain.models import (
    CompositeTableColumn,
    CompositeTablePartLayout,
    MergeColumnInfo,
    OutlineDefinition,
    PresentationProperty,
    ReportTemplate,
    SummaryRowDef,
    SummaryTableSpec,
    composite_table_part_layout_from_dict,
    composite_table_part_layout_to_dict,
)
from backend.contexts.template_catalog.infrastructure.schema import validate_report_template
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
                                                table_layout=CompositeTablePartLayout(
                                                    kind="table",
                                                    show_header=True,
                                                    columns=[
                                                        CompositeTableColumn(key="device_name", title="设备"),
                                                        CompositeTableColumn(key="status", title="状态"),
                                                        CompositeTableColumn(key="remark", title="备注"),
                                                    ],
                                                    merge_columns=[
                                                        MergeColumnInfo(title="状态说明", columns=["status", "remark"]),
                                                    ],
                                                ),
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
            template=ReportTemplate(
                id="tpl_network_daily",
                category="network_ops",
                name="网络运行日报",
                description="面向网络运维中心的统一日报模板。",
                schema_version="template.v3",
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
        self.assertEqual(composite_table.tables[0].data_properties.columns[0].key, "device_name")
        self.assertEqual(composite_table.tables[0].data_properties.merge_columns[0].title, "状态说明")
        self.assertEqual(composite_table.tables[0].data_properties.merge_columns[0].columns, ["status", "remark"])
        self.assertEqual(composite_table.tables[1].data_properties.data[0]["title"], "主要问题")

    def test_generate_report_compiles_plain_table_block_with_merge_columns(self):
        instance = _valid_template_instance()
        instance.catalogs = [
            TemplateInstanceCatalog(
                id="catalog_overview",
                title="运行概览",
                rendered_title="运行概览",
                sections=[
                    TemplateInstanceSection(
                        id="section_overview",
                        outline=OutlineDefinition(requirement="分析关键指标。", rendered_requirement="分析关键指标。", items=[]),
                        runtime_context=SectionRuntimeContext(bindings=[]),
                        content=TemplateInstanceSectionContent(
                            presentation=TemplateInstancePresentationDefinition(
                                kind="table",
                                blocks=[
                                    TemplateInstancePresentationBlock(
                                        id="block_metrics",
                                        type="table",
                                        title="关键指标明细",
                                        dataset_id="dataset_metrics",
                                        properties=PresentationProperty(
                                            merge_columns=[
                                                MergeColumnInfo(title="范围指标", columns=["scope_name", "metric_name"]),
                                            ],
                                        ),
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
            report_id="rpt_002",
            template=ReportTemplate(
                id="tpl_network_daily",
                category="network_ops",
                name="网络运行日报",
                description="面向网络运维中心的统一日报模板。",
                schema_version="template.v3",
            ),
            template_instance=instance,
        )

        table = next(component for component in report.catalogs[0].sections[0].components if isinstance(component, TableComponent))
        self.assertIsInstance(table, TableComponent)
        self.assertEqual(table.data_properties.source_id, "dataset_metrics")
        self.assertEqual(table.data_properties.merge_columns[0].title, "范围指标")
        self.assertEqual(table.data_properties.merge_columns[0].columns, ["scope_name", "metric_name"])

    def test_table_merge_columns_round_trip_domain_serializers(self):
        layout = CompositeTablePartLayout(
            kind="table",
            merge_columns=[MergeColumnInfo(title="范围指标", columns=["scope_name", "metric_name"])],
        )
        layout_payload = composite_table_part_layout_to_dict(layout)
        self.assertEqual(layout_payload["mergeColumns"][0]["columns"], ["scope_name", "metric_name"])
        self.assertEqual(
            composite_table_part_layout_from_dict(layout_payload).merge_columns[0].title,
            "范围指标",
        )

        table = TableComponent(
            id="table_metrics",
            type="table",
            data_properties=TableDataProperties(
                data_type="datasource",
                source_id="dataset_metrics",
                merge_columns=[MergeColumnInfo(title="范围指标", columns=["scope_name", "metric_name"])],
            ),
        )
        table_payload = table_component_to_dict(table)
        self.assertEqual(table_payload["dataProperties"]["mergeColumns"][0]["title"], "范围指标")
        self.assertEqual(
            table_component_from_dict(table_payload).data_properties.merge_columns[0].columns,
            ["scope_name", "metric_name"],
        )

    def test_template_schema_validates_table_merge_columns(self):
        payload = {
            "id": "tpl_merge_columns",
            "category": "network_ops",
            "name": "合并列表格模板",
            "description": "用于校验表格合并列定义。",
            "schemaVersion": "template.v3",
            "parameters": [],
            "catalogs": [
                {
                    "id": "catalog_main",
                    "title": "主目录",
                    "sections": [
                        {
                            "id": "section_main",
                            "outline": {"requirement": "展示表格。", "items": []},
                            "content": {
                                "datasets": [
                                    {"id": "dataset_metrics", "sourceType": "sql", "source": "SELECT 1"}
                                ],
                                "presentation": {
                                    "kind": "table",
                                    "blocks": [
                                        {
                                            "id": "block_metrics",
                                            "type": "table",
                                            "title": "指标表",
                                            "datasetId": "dataset_metrics",
                                            "properties": {
                                                "mergeColumns": [
                                                    {
                                                        "title": "范围指标",
                                                        "columns": ["scope_name", "metric_name"],
                                                    }
                                                ],
                                            },
                                        }
                                    ],
                                },
                            },
                        }
                    ],
                }
            ],
        }
        validate_report_template(payload)

        def assert_invalid_merge_columns(merge_columns):
            invalid_payload = copy.deepcopy(payload)
            invalid_payload["catalogs"][0]["sections"][0]["content"]["presentation"]["blocks"][0]["properties"][
                "mergeColumns"
            ] = merge_columns
            with self.assertRaises(ValueError):
                validate_report_template(invalid_payload)

        assert_invalid_merge_columns([{"title": "范围指标", "columns": ["scope_name"]}])
        assert_invalid_merge_columns([{"title": "范围指标", "columns": ["scope_name", "scope_name"]}])
        assert_invalid_merge_columns([{"columns": ["scope_name", "metric_name"]}])
        assert_invalid_merge_columns([{"title": "范围指标"}])


if __name__ == "__main__":
    unittest.main()
