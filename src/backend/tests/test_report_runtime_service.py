import copy
import unittest
from dataclasses import is_dataclass
from types import SimpleNamespace

from backend.contexts.report_runtime.application.services import ReportRuntimeService, _validate_report_dsl, build_report_dsl
from backend.contexts.report_runtime.domain.models import (
    BackCoverConfig,
    ChartComponent,
    ChartDataProperties,
    CompositeTableComponent,
    DynamicContext,
    MergeRowInfo,
    ParameterConfirmation,
    ReportAdditionalInfo,
    ReportBasicInfo,
    ReportCatalog,
    ReportColumn,
    ReportCover,
    ReportCoverContent,
    ReportDsl,
    ReportGenerateMeta,
    ReportLayout,
    ReportSection,
    ReportSlide,
    ReportSlideSection,
    ReportSummary,
    TemplateInstance,
    TemplateInstanceCatalog,
    TemplateInstanceChapter,
    TemplateInstancePresentationBlock,
    TemplateInstancePresentationDefinition,
    TemplateInstanceSlide,
    TemplateInstanceSection,
    TemplateInstanceSectionContent,
    TemplateInstanceCompositeTablePart,
    PartRuntimeContext,
    SectionRuntimeContext,
    TableComponent,
    TableDataProperties,
    TextComponent,
    TextDataProperties,
    GridDefinition,
    chart_component_from_dict,
    chart_component_to_dict,
    report_dsl_from_dict,
    report_dsl_to_dict,
    table_component_from_dict,
    table_component_to_dict,
    template_instance_from_dict,
    template_instance_presentation_block_from_dict,
    template_instance_presentation_block_to_dict,
    template_instance_to_dict,
    text_component_from_dict,
    text_component_to_dict,
)
from backend.contexts.report_runtime.domain.services import instantiate_template_instance
from backend.contexts.template_catalog.domain.models import (
    CompositeTableColumn,
    CompositeTablePartLayout,
    DynamicDefinition,
    MergeColumnInfo,
    MergeRowDefinition,
    OutlineDefinition,
    Parameter,
    ParameterValue,
    PresentationProperty,
    RequirementItem,
    ReportTemplate,
    SlideLayout,
    SummaryRowDef,
    SummaryTableSpec,
    composite_table_part_layout_from_dict,
    composite_table_part_layout_to_dict,
    presentation_block_from_dict,
    presentation_block_to_dict,
    report_template_from_dict,
    report_template_to_dict,
    dynamic_definition_from_dict,
    dynamic_definition_to_dict,
)
from backend.contexts.template_catalog.infrastructure.schema import validate_report_template, validate_template_instance
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


class _FakeCustomContentGateway:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def post_json(self, *, url, payload):
        self.requests.append({"url": url, "payload": payload})
        return self.responses.pop(0)


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
                                                        SummaryRowDef(id="action_advice", title="处理建议"),
                                                        SummaryRowDef(id="major_issue", title="问题"),
                                                        SummaryRowDef(id="risk_assessment", title="问题"),
                                                    ],
                                                ),
                                                table_layout=CompositeTablePartLayout(
                                                    kind="table",
                                                    columns=[
                                                        CompositeTableColumn(key="title", title="项目"),
                                                        CompositeTableColumn(key="content", title="内容"),
                                                    ],
                                                    merge_rows=[MergeRowDefinition(column="title")],
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
        self.assertEqual(composite_table.tables[1].data_properties.data[0]["title"], "处理建议")
        self.assertEqual(composite_table.tables[1].data_properties.merge_rows[0].start_row_index, 1)
        self.assertEqual(composite_table.tables[1].data_properties.merge_rows[0].row_span, 2)
        self.assertEqual(composite_table.tables[1].data_properties.merge_rows[0].merged_text, "问题")
        self.assertEqual(composite_table.tables[1].data_properties.merge_rows[0].column, "title")

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

    def test_generate_report_compiles_text_and_chart_blocks(self):
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
                                kind="mixed",
                                blocks=[
                                    TemplateInstancePresentationBlock(
                                        id="block_summary_text",
                                        type="text",
                                        title="态势综述",
                                        template="{$scope}运行态势综述。",
                                        content="总部网络运行态势综述。",
                                    ),
                                    TemplateInstancePresentationBlock(
                                        id="block_summary_chart",
                                        type="chart",
                                        title="关键指标趋势",
                                        dataset_id="dataset_metrics",
                                    ),
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
            report_id="rpt_003",
            template=ReportTemplate(
                id="tpl_network_daily",
                category="network_ops",
                name="网络运行日报",
                description="面向网络运维中心的统一日报模板。",
                schema_version="template.v3",
            ),
            template_instance=instance,
        )

        components = report.catalogs[0].sections[0].components
        text = next(component for component in components if isinstance(component, TextComponent))
        chart = next(component for component in components if isinstance(component, ChartComponent))

        self.assertEqual(text.data_properties.content, "总部网络运行态势综述。")
        self.assertEqual(text.data_properties.title, "态势综述")
        self.assertEqual(chart.data_properties.source_id, "dataset_metrics")
        self.assertEqual(chart.data_properties.title, "关键指标趋势")

    def test_instantiate_template_renders_text_block_template_content(self):
        template = report_template_from_dict(
            {
                "id": "tpl_text_block",
                "category": "network_ops",
                "name": "文本块模板",
                "description": "验证文本块实例化。",
                "schemaVersion": "template.v3",
                "parameters": [
                    {
                        "id": "scope",
                        "label": "分析对象",
                        "inputType": "free_text",
                        "required": True,
                        "multi": False,
                        "interactionMode": "form",
                    }
                ],
                "catalogs": [
                    {
                        "id": "catalog_main",
                        "title": "运行概览",
                        "sections": [
                            {
                                "id": "section_main",
                                "outline": {"requirement": "分析{$scope}。", "items": []},
                                "content": {
                                    "datasets": [],
                                    "presentation": {
                                        "kind": "text",
                                        "blocks": [
                                            {
                                                "id": "block_text",
                                                "type": "text",
                                                "title": "态势综述",
                                                "template": "{$scope}运行态势综述。",
                                            }
                                        ],
                                    },
                                },
                            }
                        ],
                    }
                ],
            }
        )

        instance = instantiate_template_instance(
            instance_id="ti_text",
            template=template,
            conversation_id="conv_001",
            chat_id="chat_001",
            status="collecting_parameters",
            capture_stage="fill_params",
            revision=1,
            parameter_values={
                "scope": [ParameterValue(label="总部网络", value="hq-network", query="scope_id = 'hq-network'")]
            },
        )

        block = instance.catalogs[0].sections[0].content.presentation.blocks[0]
        self.assertEqual(block.template, "{$scope}运行态势综述。")
        self.assertEqual(block.content, "总部网络运行态势综述。")

    def test_table_merge_columns_round_trip_domain_serializers(self):
        layout = CompositeTablePartLayout(
            kind="table",
            merge_columns=[MergeColumnInfo(title="范围指标", columns=["scope_name", "metric_name"])],
            merge_rows=[MergeRowDefinition(column="scope_name")],
        )
        layout_payload = composite_table_part_layout_to_dict(layout)
        self.assertEqual(layout_payload["mergeColumns"][0]["columns"], ["scope_name", "metric_name"])
        self.assertEqual(layout_payload["mergeRows"][0]["column"], "scope_name")
        self.assertEqual(
            composite_table_part_layout_from_dict(layout_payload).merge_columns[0].title,
            "范围指标",
        )
        self.assertEqual(
            composite_table_part_layout_from_dict(layout_payload).merge_rows[0].mode,
            "default",
        )

        table = TableComponent(
            id="table_metrics",
            type="table",
            data_properties=TableDataProperties(
                data_type="datasource",
                source_id="dataset_metrics",
                merge_columns=[MergeColumnInfo(title="范围指标", columns=["scope_name", "metric_name"])],
                merge_rows=[MergeRowInfo(start_row_index=0, row_span=2, column="scope_name", merged_text="总部网络")],
            ),
        )
        table_payload = table_component_to_dict(table)
        self.assertEqual(table_payload["dataProperties"]["mergeColumns"][0]["title"], "范围指标")
        self.assertEqual(table_payload["dataProperties"]["mergeRows"][0]["column"], "scope_name")
        self.assertNotIn("columnKey", table_payload["dataProperties"]["mergeRows"][0])
        self.assertEqual(
            table_component_from_dict(table_payload).data_properties.merge_columns[0].columns,
            ["scope_name", "metric_name"],
        )
        self.assertEqual(
            table_component_from_dict(table_payload).data_properties.merge_rows[0].merged_text,
            "总部网络",
        )

    def test_text_chart_and_presentation_blocks_round_trip_domain_serializers(self):
        template_block = presentation_block_from_dict(
            {"id": "block_text", "type": "text", "title": "态势综述", "template": "{$scope}运行态势综述。"}
        )
        self.assertEqual(template_block.template, "{$scope}运行态势综述。")
        self.assertEqual(presentation_block_to_dict(template_block)["properties"]["template"], "{$scope}运行态势综述。")
        self.assertNotIn("template", presentation_block_to_dict(template_block))

        instance_block = template_instance_presentation_block_from_dict(
            {
                "id": "block_text",
                "type": "text",
                "title": "态势综述",
                "template": "{$scope}运行态势综述。",
                "content": "总部网络运行态势综述。",
            }
        )
        instance_payload = template_instance_presentation_block_to_dict(instance_block)
        self.assertEqual(instance_block.template, "{$scope}运行态势综述。")
        self.assertEqual(instance_block.content, "总部网络运行态势综述。")
        self.assertEqual(instance_payload["properties"]["template"], "{$scope}运行态势综述。")
        self.assertEqual(instance_payload["properties"]["content"], "总部网络运行态势综述。")
        self.assertNotIn("template", instance_payload)
        self.assertNotIn("content", instance_payload)

        text = TextComponent(
            id="text_summary",
            type="text",
            data_properties=TextDataProperties(data_type="static", content="总部网络运行态势综述。", title="态势综述"),
        )
        text_payload = text_component_to_dict(text)
        self.assertEqual(text_payload["dataProperties"]["content"], "总部网络运行态势综述。")
        self.assertEqual(text_component_from_dict(text_payload).data_properties.title, "态势综述")

        chart = ChartComponent(
            id="chart_metrics",
            type="chart",
            data_properties=ChartDataProperties(data_type="datasource", source_id="dataset_metrics", title="关键指标趋势"),
        )
        chart_payload = chart_component_to_dict(chart)
        self.assertEqual(chart_payload["dataProperties"]["sourceId"], "dataset_metrics")
        self.assertEqual(chart_component_from_dict(chart_payload).data_properties.title, "关键指标趋势")

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
                                                "mergeRows": [
                                                    {"column": "scope_name"},
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

        def assert_invalid_merge_rows(merge_rows):
            invalid_payload = copy.deepcopy(payload)
            invalid_payload["catalogs"][0]["sections"][0]["content"]["presentation"]["blocks"][0]["properties"][
                "mergeRows"
            ] = merge_rows
            with self.assertRaises(ValueError):
                validate_report_template(invalid_payload)

        assert_invalid_merge_rows([{"mode": "default"}])
        assert_invalid_merge_rows([{"column": ""}])
        assert_invalid_merge_rows([{"column": "scope_name", "mode": "custom"}])

    def test_template_schema_supports_flow_and_paged_structures(self):
        flow_payload = {
            "id": "tpl_flow",
            "category": "network_ops",
            "name": "瀑布流模板",
            "description": "用于校验缺省 flow 结构。",
            "schemaVersion": "template.v3",
            "parameters": [],
            "catalogs": [{"id": "catalog_main", "title": "主目录", "sections": []}],
        }
        validate_report_template(flow_payload)

        explicit_flow = copy.deepcopy(flow_payload)
        explicit_flow["structureType"] = "flow"
        validate_report_template(explicit_flow)

        paged_payload = {
            "id": "tpl_paged",
            "category": "network_ops",
            "name": "分页模板",
            "description": "用于校验 PPT 分页结构。",
            "schemaVersion": "template.v3",
            "structureType": "paged",
            "parameters": [],
            "chapters": [
                {
                    "id": "chapter_overview",
                    "title": "整体概览",
                    "slides": [
                        {
                            "id": "slide_kpi",
                            "title": "核心指标",
                            "subtitle": "{$report_date}",
                            "layout": {"layoutId": "title_content", "variant": "kpi_grid"},
                            "sections": [],
                        }
                    ],
                },
                {"id": "__default__", "title": "", "implicit": True, "slides": []},
            ],
        }
        validate_report_template(paged_payload)

        missing_chapters = copy.deepcopy(paged_payload)
        del missing_chapters["chapters"]
        with self.assertRaises(ValueError):
            validate_report_template(missing_chapters)

        paged_with_catalogs = copy.deepcopy(paged_payload)
        paged_with_catalogs["catalogs"] = []
        with self.assertRaises(ValueError):
            validate_report_template(paged_with_catalogs)

        flow_without_catalogs = copy.deepcopy(flow_payload)
        del flow_without_catalogs["catalogs"]
        with self.assertRaises(ValueError):
            validate_report_template(flow_without_catalogs)

        flow_with_chapters = copy.deepcopy(explicit_flow)
        flow_with_chapters["chapters"] = []
        with self.assertRaises(ValueError):
            validate_report_template(flow_with_chapters)

        chapter_without_slides = copy.deepcopy(paged_payload)
        del chapter_without_slides["chapters"][0]["slides"]
        with self.assertRaises(ValueError):
            validate_report_template(chapter_without_slides)

        slide_without_sections = copy.deepcopy(paged_payload)
        del slide_without_sections["chapters"][0]["slides"][0]["sections"]
        with self.assertRaises(ValueError):
            validate_report_template(slide_without_sections)

    def test_paged_template_model_round_trip(self):
        default_flow = report_template_from_dict(
            {
                "id": "tpl_default_flow",
                "category": "network_ops",
                "name": "默认瀑布流",
                "description": "缺省 structureType。",
                "schemaVersion": "template.v3",
                "parameters": [],
                "catalogs": [{"id": "catalog_main", "title": "主目录", "sections": []}],
            }
        )
        self.assertEqual(default_flow.structure_type, "flow")
        default_flow_payload = report_template_to_dict(default_flow)
        self.assertEqual(default_flow_payload["structureType"], "flow")
        self.assertIn("catalogs", default_flow_payload)

        paged = report_template_from_dict(
            {
                "id": "tpl_paged_model",
                "category": "network_ops",
                "name": "分页模型",
                "description": "校验 paged from/to dict。",
                "schemaVersion": "template.v3",
                "structureType": "paged",
                "parameters": [],
                "chapters": [
                    {
                        "id": "chapter_overview",
                        "title": "整体概览",
                        "slides": [
                            {
                                "id": "slide_kpi",
                                "title": "核心指标",
                                "layout": {"layoutId": "title_content", "variant": "kpi_grid"},
                                "sections": [],
                            }
                        ],
                    },
                    {"id": "__default__", "title": "", "implicit": True, "slides": []},
                ],
            }
        )
        self.assertEqual(paged.structure_type, "paged")
        self.assertEqual(paged.chapters[0].slides[0].layout.layout_id, "title_content")
        paged_payload = report_template_to_dict(paged)
        self.assertEqual(paged_payload["structureType"], "paged")
        self.assertIn("chapters", paged_payload)
        self.assertNotIn("catalogs", paged_payload)
        self.assertTrue(paged_payload["chapters"][1]["implicit"])

    def test_paged_template_instance_schema_and_model_round_trip(self):
        template = ReportTemplate(
            id="tpl_paged_instance",
            category="network_ops",
            name="分页实例模板",
            description="校验分页实例结构。",
            schema_version="template.v3",
            structure_type="paged",
        )
        instance = TemplateInstance(
            id="ti_paged",
            schema_version="template-instance.vNext-draft",
            template_id="tpl_paged_instance",
            template=template,
            conversation_id="conv_paged",
            chat_id="chat_paged",
            status="ready_for_confirmation",
            capture_stage="confirm_params",
            revision=1,
            structure_type="paged",
            parameters=[],
            parameter_confirmation=ParameterConfirmation(missing_parameter_ids=[], confirmed=True),
            chapters=[
                TemplateInstanceChapter(
                    id="chapter_overview",
                    title="整体概览",
                    slides=[
                        TemplateInstanceSlide(
                            id="slide_kpi",
                            title="核心指标",
                            layout=SlideLayout(layout_id="title_content", variant="kpi_grid"),
                            sections=[],
                        )
                    ],
                )
            ],
        )
        payload = template_instance_to_dict(instance)
        payload["createdAt"] = "2026-05-12T00:00:00Z"
        payload["updatedAt"] = "2026-05-12T00:00:00Z"
        validate_template_instance(payload)

        self.assertEqual(payload["structureType"], "paged")
        self.assertIn("chapters", payload)
        self.assertNotIn("catalogs", payload)
        round_trip = template_instance_from_dict(payload)
        self.assertEqual(round_trip.structure_type, "paged")
        self.assertEqual(round_trip.chapters[0].slides[0].layout.layout_id, "title_content")

    def test_report_dsl_schema_accepts_merge_rows_column_and_rejects_column_key(self):
        payload = {
            "basicInfo": {
                "id": "rpt_merge_rows",
                "version": "1.0.0",
                "status": "Success",
                "parameters": {},
            },
            "catalogs": [
                {
                    "id": "catalog_main",
                    "name": "主目录",
                    "sections": [
                        {
                            "id": "section_main",
                            "components": [
                                {
                                    "id": "table_metrics",
                                    "type": "table",
                                    "dataProperties": {
                                        "dataType": "static",
                                        "columns": [{"key": "scope_name", "title": "对象"}],
                                        "data": [{"scope_name": "总部"}, {"scope_name": "总部"}],
                                        "mergeRows": [
                                            {
                                                "startRowIndex": 0,
                                                "rowSpan": 2,
                                                "column": "scope_name",
                                                "mergedText": "总部",
                                            }
                                        ],
                                    },
                                }
                            ],
                        }
                    ],
                }
            ],
            "layout": {"type": "grid"},
        }
        _validate_report_dsl(payload)

        invalid_catalog_title = copy.deepcopy(payload)
        invalid_catalog_title["catalogs"][0]["title"] = invalid_catalog_title["catalogs"][0].pop("name")
        with self.assertRaises(ValidationError):
            _validate_report_dsl(invalid_catalog_title)

        invalid_payload = copy.deepcopy(payload)
        invalid_payload["catalogs"][0]["sections"][0]["components"][0]["dataProperties"]["mergeRows"][0][
            "columnKey"
        ] = "scope_name"
        del invalid_payload["catalogs"][0]["sections"][0]["components"][0]["dataProperties"]["mergeRows"][0]["column"]
        with self.assertRaises(ValidationError):
            _validate_report_dsl(invalid_payload)

    def test_report_dsl_schema_accepts_column_lineage_source_enum_values_and_ui(self):
        payload = {
            "basicInfo": {
                "id": "rpt_lineage",
                "version": "1.0.0",
                "status": "Success",
                "parameters": {},
            },
            "catalogs": [
                {
                    "id": "catalog_main",
                    "name": "主目录",
                    "sections": [
                        {
                            "id": "section_main",
                            "components": [
                                {
                                    "id": "table_metrics",
                                    "type": "table",
                                    "dataProperties": {
                                        "dataType": "static",
                                        "columns": [
                                            {
                                                "key": "scope",
                                                "title": "范围",
                                                "lineageTracing": {
                                                    "sources": [
                                                        {
                                                            "dataSourceName": "network_metrics",
                                                            "field": "scope",
                                                            "businessName": "scope",
                                                            "businessName_cn": "范围",
                                                            "enumValues": [
                                                                {"value": "hq-network", "title": "总部网络"}
                                                            ],
                                                            "ui": {"displayPriority": "high"},
                                                        }
                                                    ]
                                                },
                                            }
                                        ],
                                        "data": [{"scope": "总部网络"}],
                                    },
                                }
                            ],
                        }
                    ],
                }
            ],
            "layout": {"type": "grid"},
        }
        _validate_report_dsl(payload)

        invalid_payload = copy.deepcopy(payload)
        invalid_payload["catalogs"][0]["sections"][0]["components"][0]["dataProperties"]["columns"][0][
            "lineageTracing"
        ]["sources"][0]["enumValues"] = "hq-network"
        with self.assertRaises(ValidationError):
            _validate_report_dsl(invalid_payload)

        invalid_payload = copy.deepcopy(payload)
        invalid_payload["catalogs"][0]["sections"][0]["components"][0]["dataProperties"]["columns"][0][
            "lineageTracing"
        ]["sources"][0]["ui"] = "high"
        with self.assertRaises(ValidationError):
            _validate_report_dsl(invalid_payload)

    def test_report_dsl_schema_keeps_legacy_flow_cover_shape(self):
        payload = {
            "basicInfo": {"id": "rpt_cover", "version": "1.0.0", "status": "Success"},
            "cover": {
                "title": "网络运行日报",
                "author": "report-system",
                "date": "2026-05-12",
                "layoutTemplate": "TITLE_TOP",
                "contents": [{"type": "text", "content": "总部网络", "elementId": "cover_scope"}],
            },
            "catalogs": [],
            "layout": {"type": "grid"},
        }
        _validate_report_dsl(payload)

        invalid_cover = copy.deepcopy(payload)
        invalid_cover["cover"] = {"components": []}
        with self.assertRaises(ValidationError):
            _validate_report_dsl(invalid_cover)

        invalid_layout = copy.deepcopy(payload)
        invalid_layout["cover"]["layoutTemplate"] = "default"
        with self.assertRaises(ValidationError):
            _validate_report_dsl(invalid_layout)

    def test_report_dsl_schema_aligns_generate_meta_with_bi_engine_model(self):
        payload = {
            "basicInfo": {"id": "rpt_generate_meta"},
            "catalogs": [],
            "layout": {"type": "grid"},
            "reportMeta": {
                "section_main": {
                    "status": "Success",
                    "question": "分析总部网络总体运行态势。",
                    "additionalInfos": [
                        {"type": "SQL", "name": "核心指标 SQL", "value": "SELECT 1", "appendix": "demo"}
                    ],
                    "outline": {
                        "requirement": "分析 {@scope}。",
                        "renderedRequirement": "分析总部网络。",
                        "items": [
                            {
                                "id": "scope",
                                "label": "分析对象",
                                "kind": "parameter_ref",
                                "required": True,
                                "sourceParameterId": "scope",
                                "values": [{"label": "总部网络", "value": "hq-network", "query": "scope_id = 'hq-network'"}],
                            }
                        ],
                    },
                    "parameters": {
                        "scope": {
                            "id": "scope",
                            "label": "分析对象",
                            "inputType": "enum",
                            "required": True,
                            "multi": False,
                            "interactionMode": "form",
                            "options": [
                                {"label": "总部网络", "value": "hq-network", "query": "scope_id = 'hq-network'"}
                            ],
                        }
                    },
                }
            },
        }
        _validate_report_dsl(payload)

        for field_name in ["status", "question"]:
            invalid_payload = copy.deepcopy(payload)
            del invalid_payload["reportMeta"]["section_main"][field_name]
            with self.assertRaises(ValidationError):
                _validate_report_dsl(invalid_payload)

        for field_name in ["additionalInfo", "summary", "sql", "api", "knowledge", "prompt"]:
            invalid_payload = copy.deepcopy(payload)
            invalid_payload["reportMeta"]["section_main"][field_name] = [] if field_name == "additionalInfo" else "legacy"
            with self.assertRaises(ValidationError):
                _validate_report_dsl(invalid_payload)

        invalid_content = copy.deepcopy(payload)
        invalid_content["reportMeta"]["section_main"]["additionalInfos"][0]["content"] = "SELECT 1"
        with self.assertRaises(ValidationError):
            _validate_report_dsl(invalid_content)

        outline_without_rendered = copy.deepcopy(payload)
        del outline_without_rendered["reportMeta"]["section_main"]["outline"]["renderedRequirement"]
        _validate_report_dsl(outline_without_rendered)

        invalid_outline = copy.deepcopy(payload)
        del invalid_outline["reportMeta"]["section_main"]["outline"]["requirement"]
        with self.assertRaises(ValidationError):
            _validate_report_dsl(invalid_outline)

        invalid_outline_item = copy.deepcopy(payload)
        del invalid_outline_item["reportMeta"]["section_main"]["outline"]["items"][0]["label"]
        with self.assertRaises(ValidationError):
            _validate_report_dsl(invalid_outline_item)

        invalid_parameter = copy.deepcopy(payload)
        del invalid_parameter["reportMeta"]["section_main"]["parameters"]["scope"]["inputType"]
        with self.assertRaises(ValidationError):
            _validate_report_dsl(invalid_parameter)

    def test_report_dsl_schema_accepts_paged_content_and_rejects_mixed_content(self):
        slide = {
            "id": "slide_overview",
            "title": "概览页",
            "layout": {"type": "grid", "grid": {"cols": 12, "rowHeight": 24}},
            "components": [
                {
                    "id": "text_overview",
                    "type": "text",
                    "dataProperties": {"dataType": "static", "content": "分页报告概览"},
                }
            ],
        }
        section = {
            "id": "section_overview",
            "type": "section",
            "title": "整体概览",
            "slides": [slide],
        }
        _validate_report_dsl({"structureType": "paged", "basicInfo": {"id": "rpt_paged"}, "content": [slide]})
        _validate_report_dsl({"structureType": "paged", "basicInfo": {"id": "rpt_paged"}, "content": [section]})

        with self.assertRaises(ValidationError):
            _validate_report_dsl({"structureType": "paged", "basicInfo": {"id": "rpt_paged"}, "content": [slide, section]})

        with self.assertRaises(ValidationError):
            _validate_report_dsl(
                {
                    "structureType": "paged",
                    "basicInfo": {"id": "rpt_paged"},
                    "content": [slide],
                    "catalogs": [],
                }
            )

    def test_report_dsl_paged_domain_round_trip(self):
        report = ReportDsl(
            structure_type="paged",
            basic_info=ReportBasicInfo(id="rpt_paged", schema_version="1.0.0", status="Success", name="PPT 报告"),
            content=[
                ReportSlideSection(
                    id="chapter_overview",
                    title="整体概览",
                    slides=[
                        ReportSlide(
                            id="slide_overview",
                            title="概览页",
                            layout=ReportLayout(type="grid", grid=GridDefinition(cols=12, row_height=24)),
                            components=[
                                TextComponent(
                                    id="text_overview",
                                    type="text",
                                    data_properties=TextDataProperties(data_type="static", content="分页报告概览"),
                                )
                            ],
                        )
                    ],
                )
            ],
        )

        payload = report_dsl_to_dict(report)
        self.assertEqual(payload["structureType"], "paged")
        self.assertIn("content", payload)
        self.assertNotIn("catalogs", payload)
        _validate_report_dsl(payload)

        restored = report_dsl_from_dict(payload)
        self.assertEqual(restored.structure_type, "paged")
        self.assertEqual(restored.content[0].slides[0].id, "slide_overview")

    def test_report_dsl_flow_cover_domain_round_trip(self):
        report = ReportDsl(
            basic_info=ReportBasicInfo(id="rpt_cover", schema_version="1.0.0", status="Success"),
            cover=ReportCover(
                title="网络运行日报",
                author="report-system",
                date="2026-05-12",
                layout_template="TITLE_CENTER",
                contents=[ReportCoverContent(type="text", content="总部网络", element_id="cover_scope")],
            ),
            catalogs=[ReportCatalog(id="catalog_main", name="主目录", sections=[])],
            layout=ReportLayout(type="grid", grid=GridDefinition(cols=12, row_height=24)),
        )

        payload = report_dsl_to_dict(report)
        self.assertEqual(payload["cover"]["title"], "网络运行日报")
        self.assertEqual(payload["cover"]["contents"][0]["elementId"], "cover_scope")
        self.assertEqual(payload["catalogs"][0]["name"], "主目录")
        self.assertNotIn("title", payload["catalogs"][0])
        _validate_report_dsl(payload)

        restored = report_dsl_from_dict(payload)
        self.assertEqual(restored.cover.title, "网络运行日报")
        self.assertEqual(restored.cover.contents[0].element_id, "cover_scope")

    def test_report_dsl_schema_enhancements_round_trip(self):
        report = ReportDsl(
            basic_info=ReportBasicInfo(
                id="rpt_enhanced",
                asset_schema_version="1.0.0",
                schema_version="1.1.0",
                mode="published",
                status="Success",
                name="增强报告",
                title="增强报告标题",
                sub_title="增强副标题",
                template_id="tpl_enhanced",
                template_name="增强模板",
                remark="补齐 BI Engine 字段",
                create_date="2026-05-13",
                modify_date="2026-05-13",
                creator="creator",
                modifier="modifier",
                header="页眉",
                footer="页脚",
                category="network_ops",
            ),
            catalogs=[
                ReportCatalog(
                    id="catalog_enhanced",
                    name="增强目录",
                    sections=[
                        ReportSection(
                            id="section_enhanced",
                            title="增强章节",
                            components=[
                                TableComponent(
                                    id="table_enhanced",
                                    type="table",
                                    data_properties=TableDataProperties(
                                        data_type="static",
                                        title="增强表格",
                                        columns=[
                                            ReportColumn(
                                                key="scope",
                                                title="范围",
                                                type="string",
                                                width=120,
                                                sortable=True,
                                                filterable=True,
                                            )
                                        ],
                                        merge_columns=[
                                            MergeColumnInfo(
                                                title="合并列",
                                                columns=["scope", "metric"],
                                                is_merge_value=True,
                                            )
                                        ],
                                        has_merge=True,
                                    ),
                                    advance_properties={
                                        "showHeader": True,
                                        "showTitle": True,
                                        "pagination": {"showPagination": True, "defaultDisplayRows": 10},
                                    },
                                ),
                                ChartComponent(
                                    id="chart_enhanced",
                                    type="chart",
                                    data_properties=ChartDataProperties(
                                        data_type="static",
                                        columns=[ReportColumn(key="date", title="日期")],
                                        data=[{"date": "2026-05-13", "availability": 99.98}],
                                        series=[
                                            {
                                                "type": "line",
                                                "name": "可用率",
                                                "encode": {"x": "date", "y": "availability"},
                                            }
                                        ],
                                        axis_group=["primary"],
                                        x_axis={"type": "category", "name": "日期"},
                                        y_axis={"type": "value", "name": "可用率"},
                                    ),
                                    options={"responsive": {"enabled": True, "aspectRatio": 1.6}},
                                ),
                            ],
                        )
                    ],
                )
            ],
            layout=ReportLayout(type="grid", auto_layout=True, grid=GridDefinition(cols=12, row_height=24)),
            back_cover=BackCoverConfig(image="https://example.test/back-cover.png", text="Thank You"),
            report_meta={
                "section_enhanced": ReportGenerateMeta(
                    status="Success",
                    question="分析核心指标。",
                    additional_infos=[
                        ReportAdditionalInfo(
                            type="SQL",
                            name="核心 SQL",
                            value="SELECT 1",
                            appendix="执行证据",
                        )
                    ],
                    outline=OutlineDefinition(
                        requirement="分析 {@scope} 的核心指标。",
                        rendered_requirement="分析总部网络的核心指标。",
                        items=[
                            RequirementItem(
                                id="scope",
                                label="分析对象",
                                kind="parameter_ref",
                                required=True,
                                source_parameter_id="scope",
                                values=[ParameterValue(label="总部网络", value="hq-network", query="scope_id = 'hq-network'")],
                            )
                        ],
                    ),
                    parameters={
                        "scope": Parameter(
                            id="scope",
                            label="分析对象",
                            input_type="enum",
                            required=True,
                            multi=False,
                            interaction_mode="form",
                            options=[
                                ParameterValue(
                                    label="总部网络",
                                    value="hq-network",
                                    query="scope_id = 'hq-network'",
                                )
                            ],
                        )
                    },
                )
            },
        )

        payload = report_dsl_to_dict(report)
        _validate_report_dsl(payload)
        self.assertEqual(payload["backCover"]["text"], "Thank You")
        self.assertEqual(payload["basicInfo"]["schemaVersion"], "1.0.0")
        self.assertEqual(payload["basicInfo"]["subTitle"], "增强副标题")
        self.assertTrue(payload["layout"]["autoLayout"])
        table_data = payload["catalogs"][0]["sections"][0]["components"][0]["dataProperties"]
        self.assertTrue(table_data["columns"][0]["sortable"])
        self.assertTrue(table_data["mergeColumns"][0]["isMergeValue"])
        chart = payload["catalogs"][0]["sections"][0]["components"][1]
        self.assertEqual(chart["dataProperties"]["series"][0]["type"], "line")
        self.assertEqual(chart["dataProperties"]["xAxis"]["type"], "category")
        self.assertNotIn("xAxis", chart)
        self.assertTrue(chart["options"]["responsive"]["enabled"])
        meta_payload = payload["reportMeta"]["section_enhanced"]
        additional_info = meta_payload["additionalInfos"][0]
        self.assertEqual(additional_info["value"], "SELECT 1")
        self.assertEqual(additional_info["appendix"], "执行证据")
        self.assertEqual(meta_payload["outline"]["items"][0]["sourceParameterId"], "scope")
        self.assertEqual(meta_payload["outline"]["items"][0]["values"][0]["value"], "hq-network")
        self.assertEqual(meta_payload["parameters"]["scope"]["inputType"], "enum")
        self.assertNotIn("additionalInfo", meta_payload)

        restored = report_dsl_from_dict(payload)
        restored_payload = report_dsl_to_dict(restored)
        _validate_report_dsl(restored_payload)
        self.assertEqual(restored_payload["basicInfo"]["schemaVersion"], "1.0.0")
        self.assertEqual(restored_payload["backCover"]["image"], "https://example.test/back-cover.png")
        self.assertEqual(restored_payload["catalogs"][0]["sections"][0]["components"][1]["dataProperties"]["xAxis"]["type"], "category")

        legacy_chart_payload = copy.deepcopy(payload)
        legacy_chart = legacy_chart_payload["catalogs"][0]["sections"][0]["components"][1]
        legacy_chart["xAxis"] = legacy_chart["dataProperties"].pop("xAxis")
        legacy_chart["yAxis"] = legacy_chart["dataProperties"].pop("yAxis")
        restored_legacy_chart = report_dsl_from_dict(legacy_chart_payload)
        restored_legacy_chart_payload = report_dsl_to_dict(restored_legacy_chart)
        self.assertEqual(restored_legacy_chart_payload["catalogs"][0]["sections"][0]["components"][1]["dataProperties"]["xAxis"]["type"], "category")
        self.assertNotIn("xAxis", restored_legacy_chart_payload["catalogs"][0]["sections"][0]["components"][1])

        legacy_payload = copy.deepcopy(payload)
        legacy_payload["reportMeta"]["section_enhanced"]["additionalInfo"] = legacy_payload["reportMeta"]["section_enhanced"].pop("additionalInfos")
        legacy_payload["reportMeta"]["section_enhanced"]["additionalInfo"][0]["content"] = legacy_payload["reportMeta"]["section_enhanced"]["additionalInfo"][0].pop("value")
        legacy_payload["reportMeta"]["section_enhanced"]["summary"] = "旧摘要字段"
        legacy_payload["reportMeta"]["section_enhanced"]["sql"] = "SELECT 2"
        restored_legacy = report_dsl_from_dict(legacy_payload)
        self.assertEqual(restored_legacy.report_meta["section_enhanced"].additional_infos[0].value, "SELECT 1")
        restored_legacy_payload = report_dsl_to_dict(restored_legacy)
        self.assertIn("additionalInfos", restored_legacy_payload["reportMeta"]["section_enhanced"])
        self.assertNotIn("additionalInfo", restored_legacy_payload["reportMeta"]["section_enhanced"])
        self.assertNotIn("summary", restored_legacy_payload["reportMeta"]["section_enhanced"])
        self.assertEqual(restored_legacy.report_meta["section_enhanced"].additional_infos[1].type, "Summary")
        self.assertEqual(restored_legacy.report_meta["section_enhanced"].additional_infos[2].type, "SQL")

    def test_schema_validates_supported_presentation_block_types(self):
        template_payload = {
            "id": "tpl_presentation_types",
            "category": "network_ops",
            "name": "展示类型模板",
            "description": "用于校验展示类型。",
            "schemaVersion": "template.v3",
            "parameters": [],
            "catalogs": [
                {
                    "id": "catalog_main",
                    "title": "主目录",
                    "sections": [
                        {
                            "id": "section_main",
                            "outline": {"requirement": "展示内容。", "items": []},
                            "content": {
                                "datasets": [
                                    {"id": "dataset_metrics", "sourceType": "sql", "source": "SELECT 1"}
                                ],
                                "presentation": {
                                    "kind": "mixed",
                                    "blocks": [
                                        {
                                            "id": "block_text",
                                            "type": "text",
                                            "title": "态势综述",
                                            "properties": {"template": "运行态势综述。"},
                                        },
                                        {
                                            "id": "block_chart",
                                            "type": "chart",
                                            "title": "趋势图",
                                            "datasetId": "dataset_metrics",
                                        },
                                        {
                                            "id": "block_table",
                                            "type": "table",
                                            "title": "明细表",
                                            "datasetId": "dataset_metrics",
                                        },
                                        {
                                            "id": "block_composite",
                                            "type": "composite_table",
                                            "title": "复合表",
                                            "parts": [
                                                {
                                                    "id": "part_metrics",
                                                    "title": "指标",
                                                    "sourceType": "query",
                                                    "datasetId": "dataset_metrics",
                                                }
                                            ],
                                        },
                                    ],
                                },
                            },
                        }
                    ],
                }
            ],
        }
        validate_report_template(template_payload)

        instance_payload = {
            "id": "ti_001",
            "schemaVersion": "template-instance.vNext-draft",
            "templateId": "tpl_presentation_types",
            "template": {
                "id": "tpl_presentation_types",
                "category": "network_ops",
                "name": "展示类型模板",
                "description": "用于校验展示类型。",
                "schemaVersion": "template.v3",
                "parameters": [],
                "catalogs": [],
            },
            "conversationId": "conv_001",
            "chatId": "chat_001",
            "status": "ready_for_confirmation",
            "captureStage": "confirm_params",
            "revision": 1,
            "parameters": [],
            "parameterConfirmation": {"missingParameterIds": [], "confirmed": True},
            "catalogs": [
                {
                    "id": "catalog_main",
                    "title": "主目录",
                    "renderedTitle": "主目录",
                    "sections": [
                        {
                            "id": "section_main",
                            "outline": {"requirement": "展示内容。", "renderedRequirement": "展示内容。", "items": []},
                            "content": {
                                "datasets": [],
                                "presentation": {
                                    "kind": "text",
                                    "blocks": [
                                        {
                                            "id": "block_text",
                                            "type": "text",
                                            "title": "态势综述",
                                            "properties": {
                                                "template": "运行态势综述。",
                                                "content": "运行态势综述。",
                                            },
                                        }
                                    ],
                                },
                            },
                            "runtimeContext": {"bindings": []},
                            "skeletonStatus": "reusable",
                            "userEdited": False,
                        }
                    ],
                }
            ],
            "createdAt": "2026-05-08T00:00:00Z",
            "updatedAt": "2026-05-08T00:00:00Z",
        }
        validate_template_instance(instance_payload)

        invalid_instance_payload = copy.deepcopy(instance_payload)
        del invalid_instance_payload["catalogs"][0]["sections"][0]["content"]["presentation"]["blocks"][0]["properties"]["content"]
        with self.assertRaises(ValueError):
            validate_template_instance(invalid_instance_payload)

        invalid_text_payload = copy.deepcopy(template_payload)
        del invalid_text_payload["catalogs"][0]["sections"][0]["content"]["presentation"]["blocks"][0]["properties"]["template"]
        with self.assertRaises(ValueError):
            validate_report_template(invalid_text_payload)

        for unsupported_type in ["paragraph", "bullet", "kpi", "markdown"]:
            invalid_type_payload = copy.deepcopy(template_payload)
            invalid_type_payload["catalogs"][0]["sections"][0]["content"]["presentation"]["blocks"][0]["type"] = unsupported_type
            with self.assertRaises(ValueError):
                validate_report_template(invalid_type_payload)

    def test_dynamic_schema_accepts_foreach_case_and_rejects_legacy_foreach(self):
        payload = {
            "id": "tpl_dynamic",
            "category": "network_ops",
            "name": "动态目录模板",
            "description": "用于校验 dynamic 定义。",
            "schemaVersion": "template.v3",
            "parameters": [
                {
                    "id": "scope",
                    "label": "分析对象",
                    "inputType": "enum",
                    "required": True,
                    "multi": True,
                    "interactionMode": "form",
                    "options": [
                        {"label": "总部", "value": "hq", "query": "scope = 'hq'"},
                        {"label": "分支", "value": "branch", "query": "scope = 'branch'"},
                    ],
                }
            ],
            "catalogs": [
                {
                    "id": "catalog_dynamic",
                    "title": "{$scope} 分支分析",
                    "dynamic": {
                        "type": "foreachCase",
                        "parameterId": "scope",
                        "as": "scope_item",
                        "cases": [
                            {
                                "id": "hq_case",
                                "values": ["hq"],
                                "sections": [
                                    {
                                        "id": "section_hq",
                                        "outline": {"requirement": "分析总部。", "items": []},
                                        "content": {"presentation": {"kind": "text", "blocks": []}},
                                    }
                                ],
                            }
                        ],
                    },
                }
            ],
        }
        validate_report_template(payload)

        invalid_legacy = copy.deepcopy(payload)
        invalid_legacy["catalogs"][0].pop("dynamic")
        invalid_legacy["catalogs"][0]["foreach"] = {"parameterId": "scope", "as": "scope_item"}
        with self.assertRaises(ValueError):
            validate_report_template(invalid_legacy)

        invalid_case = copy.deepcopy(payload)
        del invalid_case["catalogs"][0]["dynamic"]["cases"][0]["values"]
        with self.assertRaises(ValueError):
            validate_report_template(invalid_case)

    def test_legacy_foreach_input_serializes_as_dynamic(self):
        template = report_template_from_dict(
            {
                "id": "tpl_legacy_foreach",
                "category": "network_ops",
                "name": "旧 foreach 模板",
                "description": "用于校验兼容读取。",
                "schemaVersion": "template.v3",
                "parameters": [],
                "catalogs": [
                    {
                        "id": "catalog_scope",
                        "title": "{$scope} 分析",
                        "foreach": {"parameterId": "scope", "as": "scope_item"},
                        "sections": [],
                    }
                ],
            }
        )

        self.assertEqual(template.catalogs[0].dynamic.type, "foreach")
        self.assertEqual(template.catalogs[0].foreach.parameter_id, "scope")
        payload = report_template_to_dict(template)
        self.assertEqual(payload["catalogs"][0]["dynamic"]["type"], "foreach")
        self.assertNotIn("foreach", payload["catalogs"][0])

    def test_dynamic_custom_schema_and_model_contract(self):
        payload = {
            "id": "tpl_custom_dynamic",
            "category": "network_ops",
            "name": "外部内容模板",
            "description": "用于校验 dynamic custom。",
            "schemaVersion": "template.v3",
            "parameters": [],
            "catalogs": [
                {
                    "id": "catalog_custom",
                    "title": "外部目录",
                    "dynamic": {"type": "custom", "url": "https://example.test/catalog"},
                },
                {
                    "id": "catalog_main",
                    "title": "主目录",
                    "sections": [
                        {
                            "id": "section_custom",
                            "dynamic": {"type": "custom", "url": "https://example.test/section"},
                            "outline": {"requirement": "生成外部章节。", "items": []},
                        }
                    ],
                },
            ],
        }
        validate_report_template(payload)

        invalid_without_url = copy.deepcopy(payload)
        del invalid_without_url["catalogs"][0]["dynamic"]["url"]
        with self.assertRaises(ValueError):
            validate_report_template(invalid_without_url)

        invalid_with_config = copy.deepcopy(payload)
        invalid_with_config["catalogs"][0]["dynamic"]["config"] = {}
        with self.assertRaises(ValueError):
            validate_report_template(invalid_with_config)

        invalid_section_without_outline = copy.deepcopy(payload)
        del invalid_section_without_outline["catalogs"][1]["sections"][0]["outline"]
        with self.assertRaises(ValueError):
            validate_report_template(invalid_section_without_outline)

        dynamic = dynamic_definition_from_dict({"type": "custom", "url": "https://example.test/section"})
        self.assertEqual(dynamic.url, "https://example.test/section")
        self.assertEqual(dynamic_definition_to_dict(dynamic), {"type": "custom", "url": "https://example.test/section"})

    def test_dynamic_custom_v6_paged_schema_contract(self):
        payload = {
            "id": "tpl_paged_custom_dynamic",
            "category": "network_ops",
            "name": "分页外部内容模板",
            "description": "用于校验 dynamic custom v6 分页契约。",
            "schemaVersion": "template.v3",
            "structureType": "paged",
            "parameters": [
                {
                    "id": "scope",
                    "label": "范围",
                    "inputType": "enum",
                    "required": True,
                    "multi": False,
                    "interactionMode": "form",
                    "options": [{"label": "总部", "value": "hq", "query": "scope = 'hq'"}],
                }
            ],
            "chapters": [
                {
                    "id": "chapter_overview",
                    "title": "整体概览",
                    "slides": [
                        {
                            "id": "slide_custom",
                            "title": "外部页面",
                            "dynamic": {"type": "custom", "url": "https://example.test/slide"},
                            "sections": [],
                        },
                        {
                            "id": "slide_mixed",
                            "title": "混合页面",
                            "sections": [
                                {
                                    "id": "section_custom",
                                    "dynamic": {"type": "custom", "url": "https://example.test/components"},
                                    "outline": {"requirement": "生成页面内组件。", "items": []},
                                }
                            ],
                        },
                    ],
                }
            ],
        }
        validate_report_template(payload)

        invalid_chapter_custom = copy.deepcopy(payload)
        invalid_chapter_custom["chapters"][0]["dynamic"] = {
            "type": "custom",
            "url": "https://example.test/chapter",
        }
        with self.assertRaises(ValueError):
            validate_report_template(invalid_chapter_custom)

        chapter_foreach = copy.deepcopy(payload)
        chapter_foreach["chapters"][0]["dynamic"] = {
            "type": "foreach",
            "parameterId": "scope",
            "as": "currentScope",
        }
        validate_report_template(chapter_foreach)

        invalid_section_without_outline = copy.deepcopy(payload)
        del invalid_section_without_outline["chapters"][0]["slides"][1]["sections"][0]["outline"]
        with self.assertRaises(ValueError):
            validate_report_template(invalid_section_without_outline)

    def test_dynamic_custom_context_round_trip(self):
        instance = _valid_template_instance()
        instance.catalogs = [
            TemplateInstanceCatalog(
                id="catalog_custom",
                title="外部目录",
                rendered_title="外部目录",
                dynamic_context=DynamicContext(type="custom", url="https://example.test/catalog", node_type="catalog"),
                sections=[],
            )
        ]
        payload = template_instance_to_dict(instance)
        payload["createdAt"] = "2026-05-09T00:00:00Z"
        payload["updatedAt"] = "2026-05-09T00:00:00Z"
        payload["template"]["createdAt"] = "2026-05-09T00:00:00Z"
        payload["template"]["updatedAt"] = "2026-05-09T00:00:00Z"
        validate_template_instance(payload)

        self.assertEqual(payload["catalogs"][0]["dynamicContext"]["type"], "custom")
        self.assertEqual(payload["catalogs"][0]["dynamicContext"]["url"], "https://example.test/catalog")
        self.assertEqual(payload["catalogs"][0]["dynamicContext"]["nodeType"], "catalog")
        restored = template_instance_from_dict(payload)
        self.assertEqual(restored.catalogs[0].dynamic_context.type, "custom")
        self.assertEqual(restored.catalogs[0].dynamic_context.url, "https://example.test/catalog")

    def test_dynamic_custom_slide_context_round_trip(self):
        instance = _valid_template_instance()
        instance.structure_type = "paged"
        instance.catalogs = []
        instance.chapters = [
            TemplateInstanceChapter(
                id="chapter_overview",
                title="整体概览",
                slides=[
                    TemplateInstanceSlide(
                        id="slide_custom",
                        title="外部页面",
                        dynamic_context=DynamicContext(
                            type="custom",
                            url="https://example.test/slide",
                            node_type="slide",
                        ),
                        sections=[],
                    )
                ],
            )
        ]
        payload = template_instance_to_dict(instance)
        payload["createdAt"] = "2026-05-09T00:00:00Z"
        payload["updatedAt"] = "2026-05-09T00:00:00Z"
        payload["template"]["createdAt"] = "2026-05-09T00:00:00Z"
        payload["template"]["updatedAt"] = "2026-05-09T00:00:00Z"
        validate_template_instance(payload)

        dynamic_context = payload["chapters"][0]["slides"][0]["dynamicContext"]
        self.assertEqual(dynamic_context["type"], "custom")
        self.assertEqual(dynamic_context["url"], "https://example.test/slide")
        self.assertEqual(dynamic_context["nodeType"], "slide")
        restored = template_instance_from_dict(payload)
        self.assertEqual(restored.chapters[0].slides[0].dynamic_context.node_type, "slide")

    def test_build_report_dsl_uses_custom_catalog_response(self):
        instance = _valid_template_instance()
        instance.parameters = []
        scope_value = ParameterValue(label="总部", value="hq", query="scope = 'hq'")
        instance.catalogs = [
            TemplateInstanceCatalog(
                id="catalog_custom",
                title="{$scope} 外部目录",
                rendered_title="总部 外部目录",
                parameters=[
                    Parameter(
                        id="scope",
                        label="分析对象",
                        input_type="enum",
                        required=True,
                        multi=False,
                        interaction_mode="form",
                        values=[scope_value],
                    )
                ],
                dynamic_context=DynamicContext(type="custom", url="https://example.test/catalog", node_type="catalog"),
                sections=[],
            )
        ]
        gateway = _FakeCustomContentGateway(
            [
                {
                    "id": "catalog_external",
                    "name": "外部返回目录",
                    "sections": [
                        {
                            "id": "section_external",
                            "title": "外部章节",
                            "components": [
                                {
                                    "id": "component_external",
                                    "type": "markdown",
                                    "dataProperties": {"dataType": "static", "content": "外部内容"},
                                }
                            ],
                        }
                    ],
                }
            ]
        )

        report = build_report_dsl(
            report_id="rpt_custom_catalog",
            template=ReportTemplate(
                id="tpl_custom",
                category="network_ops",
                name="外部内容模板",
                description="验证 custom catalog。",
                schema_version="template.v3",
            ),
            template_instance=instance,
            custom_content_gateway=gateway,
        )

        self.assertEqual(report.catalogs[0].id, "catalog_external")
        self.assertEqual(report.catalogs[0].sections[0].id, "section_external")
        self.assertEqual(gateway.requests[0]["url"], "https://example.test/catalog")
        self.assertEqual(gateway.requests[0]["payload"]["nodeType"], "catalog")
        self.assertEqual(gateway.requests[0]["payload"]["nodeId"], "catalog_custom")
        self.assertEqual(gateway.requests[0]["payload"]["prompt"], "总部 外部目录")
        self.assertEqual(gateway.requests[0]["payload"]["parameters"]["scope"][0]["value"], "hq")

    def test_build_report_dsl_uses_custom_section_response(self):
        scope_value = ParameterValue(label="总部", value="hq", query="scope = 'hq'")
        instance = _valid_template_instance()
        instance.catalogs = [
            TemplateInstanceCatalog(
                id="catalog_main",
                title="主目录",
                rendered_title="主目录",
                parameters=[
                    Parameter(
                        id="scope",
                        label="分析对象",
                        input_type="enum",
                        required=True,
                        multi=False,
                        interaction_mode="form",
                        values=[scope_value],
                    )
                ],
                sections=[
                    TemplateInstanceSection(
                        id="section_custom",
                        outline=OutlineDefinition(
                            requirement="生成{$scope}外部章节。",
                            rendered_requirement="生成总部外部章节。",
                            items=[],
                        ),
                        content=TemplateInstanceSectionContent(
                            presentation=TemplateInstancePresentationDefinition(kind="mixed", blocks=[])
                        ),
                        runtime_context=SectionRuntimeContext(bindings=[]),
                        skeleton_status="reusable",
                        user_edited=True,
                        dynamic_context=DynamicContext(type="custom", url="https://example.test/section", node_type="section"),
                    )
                ],
            )
        ]
        gateway = _FakeCustomContentGateway(
            [
                {
                    "id": "section_external",
                    "title": "外部章节",
                    "components": [
                        {
                            "id": "component_external",
                            "type": "markdown",
                            "dataProperties": {"dataType": "static", "content": "外部章节内容"},
                        }
                    ],
                    "summary": {"id": "summary_section_external", "overview": "外部摘要"},
                }
            ]
        )

        report = build_report_dsl(
            report_id="rpt_custom_section",
            template=ReportTemplate(
                id="tpl_custom",
                category="network_ops",
                name="外部内容模板",
                description="验证 custom section。",
                schema_version="template.v3",
            ),
            template_instance=instance,
            custom_content_gateway=gateway,
        )

        self.assertEqual(report.catalogs[0].sections[0].id, "section_external")
        self.assertEqual(report.catalogs[0].sections[0].summary.overview, "外部摘要")
        self.assertEqual(gateway.requests[0]["url"], "https://example.test/section")
        self.assertEqual(gateway.requests[0]["payload"]["nodeType"], "section")
        self.assertEqual(gateway.requests[0]["payload"]["nodeId"], "section_custom")
        self.assertEqual(gateway.requests[0]["payload"]["prompt"], "生成总部外部章节。")
        self.assertEqual(gateway.requests[0]["payload"]["parameters"]["scope"][0]["label"], "总部")

    def test_instantiate_template_expands_catalog_foreach_case(self):
        template = report_template_from_dict(
            {
                "id": "tpl_catalog_foreach_case",
                "category": "network_ops",
                "name": "目录 foreachCase 模板",
                "description": "用于校验目录级 foreachCase。",
                "schemaVersion": "template.v3",
                "parameters": [
                    {
                        "id": "scope",
                        "label": "分析对象",
                        "inputType": "enum",
                        "required": True,
                        "multi": True,
                        "interactionMode": "form",
                        "options": [
                            {"label": "总部", "value": "hq", "query": "scope = 'hq'"},
                            {"label": "分支", "value": "branch", "query": "scope = 'branch'"},
                            {"label": "未知", "value": "unknown", "query": "scope = 'unknown'"},
                        ],
                    }
                ],
                "catalogs": [
                    {
                        "id": "catalog_dynamic",
                        "title": "{$scope} 分支分析",
                        "dynamic": {
                            "type": "foreachCase",
                            "parameterId": "scope",
                            "as": "scope_item",
                            "cases": [
                                {
                                    "id": "hq_case",
                                    "values": ["hq"],
                                    "sections": [
                                        {
                                            "id": "section_hq",
                                            "outline": {"requirement": "分析总部。", "items": []},
                                            "content": {"presentation": {"kind": "text", "blocks": []}},
                                        }
                                    ],
                                },
                                {
                                    "id": "branch_case",
                                    "values": ["branch"],
                                    "sections": [
                                        {
                                            "id": "section_branch",
                                            "outline": {"requirement": "分析分支。", "items": []},
                                            "content": {"presentation": {"kind": "text", "blocks": []}},
                                        }
                                    ],
                                },
                            ],
                            "defaultCase": {
                                "sections": [
                                    {
                                        "id": "section_default",
                                        "outline": {"requirement": "分析默认对象。", "items": []},
                                        "content": {"presentation": {"kind": "text", "blocks": []}},
                                    }
                                ]
                            },
                        },
                    }
                ],
            }
        )

        instance = instantiate_template_instance(
            instance_id="ti_catalog_case",
            template=template,
            conversation_id="conv_001",
            chat_id="chat_001",
            status="collecting_parameters",
            capture_stage="fill_params",
            revision=1,
            parameter_values={
                "scope": [
                    ParameterValue(label="总部", value="hq", query="scope = 'hq'"),
                    ParameterValue(label="分支", value="branch", query="scope = 'branch'"),
                    ParameterValue(label="未知", value="unknown", query="scope = 'unknown'"),
                ]
            },
        )

        self.assertEqual([catalog.sections[0].id for catalog in instance.catalogs], ["section_hq", "section_branch", "section_default"])
        self.assertEqual([catalog.dynamic_context.case_id for catalog in instance.catalogs], ["hq_case", "branch_case", None])
        self.assertEqual(instance.catalogs[0].dynamic_context.item_value.value, "hq")

    def test_instantiate_template_expands_section_foreach_case(self):
        template = report_template_from_dict(
            {
                "id": "tpl_section_foreach_case",
                "category": "network_ops",
                "name": "章节 foreachCase 模板",
                "description": "用于校验章节级 foreachCase。",
                "schemaVersion": "template.v3",
                "parameters": [
                    {
                        "id": "scope",
                        "label": "分析对象",
                        "inputType": "enum",
                        "required": True,
                        "multi": True,
                        "interactionMode": "form",
                        "options": [
                            {"label": "总部", "value": "hq", "query": "scope = 'hq'"},
                            {"label": "分支", "value": "branch", "query": "scope = 'branch'"},
                        ],
                    }
                ],
                "catalogs": [
                    {
                        "id": "catalog_main",
                        "title": "分支章节",
                        "sections": [
                            {
                                "id": "section_dynamic",
                                "dynamic": {
                                    "type": "foreachCase",
                                    "parameterId": "scope",
                                    "as": "scope_item",
                                    "cases": [
                                        {
                                            "id": "hq_case",
                                            "values": ["hq"],
                                            "sections": [
                                                {
                                                    "id": "section_hq",
                                                    "outline": {"requirement": "分析总部。", "items": []},
                                                    "content": {"presentation": {"kind": "text", "blocks": []}},
                                                }
                                            ],
                                        },
                                        {
                                            "id": "branch_case",
                                            "values": ["branch"],
                                            "sections": [
                                                {
                                                    "id": "section_branch",
                                                    "outline": {"requirement": "分析分支。", "items": []},
                                                    "content": {"presentation": {"kind": "text", "blocks": []}},
                                                }
                                            ],
                                        },
                                    ],
                                },
                            }
                        ],
                    }
                ],
            }
        )

        instance = instantiate_template_instance(
            instance_id="ti_section_case",
            template=template,
            conversation_id="conv_001",
            chat_id="chat_001",
            status="collecting_parameters",
            capture_stage="fill_params",
            revision=1,
            parameter_values={
                "scope": [
                    ParameterValue(label="总部", value="hq", query="scope = 'hq'"),
                    ParameterValue(label="分支", value="branch", query="scope = 'branch'"),
                ]
            },
        )

        self.assertEqual([section.id for section in instance.catalogs[0].sections], ["section_hq", "section_branch"])
        self.assertEqual([section.dynamic_context.case_id for section in instance.catalogs[0].sections], ["hq_case", "branch_case"])


if __name__ == "__main__":
    unittest.main()
