from __future__ import annotations

import pytest

from src.contexts.report.domain.generation_models import (
    ChartComponent,
    CompositeTableComponent,
    TableComponent,
    TextComponent,
)
from src.contexts.report.domain.report_dsl_compiler import ReportDslCompiler
from src.contexts.report.domain.template_instance_builder import instantiate_template_instance
from src.contexts.report.domain.template_models import PresentationBlock, report_template_from_dict
from src.contexts.report.application.dataset_execution_service import DatasetExecutionService
from src.contexts.report.infrastructure.template_schema import ReportDslSchemaGateway
from src.shared.kernel.errors import ValidationError
from tests.support.builders import load_json_fixture
from tests.support.mock_external import (
    COMPLEX_TEMPLATE_FIXTURES,
    FixtureExternalBusinessGateway,
    compile_complex_template,
)


@pytest.mark.parametrize("name", COMPLEX_TEMPLATE_FIXTURES)
def test_complex_development_template_compiles_to_valid_report_dsl(name):
    report = compile_complex_template(name)

    assert report.basic_info.id.startswith("rpt_")
    assert report.structure_type in {"flow", "paged"}


def test_flow_template_fills_text_table_chart_and_composite_table_from_datasets():
    report = compile_complex_template("network-device-health-inspection-flow.json")
    components = report.catalogs[0].sections[0].components

    text = next(item for item in components if isinstance(item, TextComponent))
    table = next(item for item in components if isinstance(item, TableComponent))
    chart = next(item for item in components if isinstance(item, ChartComponent))
    composite = next(item for item in components if isinstance(item, CompositeTableComponent))
    assert "核心交换机-A" in text.data_properties.content
    assert table.data_properties.data[0]["device_name"] == "核心交换机-A"
    assert chart.data_properties.data[0]["availability"] == 99.91
    assert composite.tables[0].data_properties.data[1]["status"] == "关注"
    assert report.catalogs[0].sub_catalogs[0].sections[0].title == "外部巡检建议"


def test_paged_template_merges_dynamic_components_and_slide():
    report = compile_complex_template("network-device-health-inspection-paged.json")
    slides = report.content[0].slides

    assert report.structure_type == "paged"
    assert any(item.id == "text_dynamic_paged" for item in slides[2].components)
    assert slides[3].id == "slide_external"
    assert slides[3].title == "外部运行建议"


def test_development_templates_cover_foreach_and_foreach_case_expansion():
    health_flow = compile_complex_template("network-device-health-inspection-flow.json")
    operations_flow = compile_complex_template("network-operations-status-flow.json")
    health_paged = compile_complex_template("network-device-health-inspection-paged.json")
    operations_paged = compile_complex_template("network-operations-status-paged.json")

    assert health_flow.catalogs[1].name == "核心交换机-A专项复核"
    assert operations_flow.catalogs[1].sections[0].id == "section_daily_focus"
    assert health_paged.content[0].slides[0].id == "slide_health_table_core-sw-a"
    assert operations_paged.content[0].id == "chapter_operations_24h"


@pytest.mark.parametrize("source_type", ["llm", "compose"])
def test_referenced_non_executable_dataset_returns_explicit_error(source_type):
    template = report_template_from_dict(load_json_fixture("report-templates", "network-operations-status-flow.json"))
    section = template.catalogs[0].sections[0]
    section.content.datasets.append(type(section.content.datasets[0])(id="datasetUnsupported", source_type=source_type, source_ref="unsupported"))
    section.content.presentation.blocks.append(PresentationBlock(id="tableUnsupported", type="table", dataset_id="datasetUnsupported"))
    instance = instantiate_template_instance(
        instance_id="ti_unsupported",
        template=template,
        conversation_id="conv",
        chat_id="chat",
        status="ready_for_confirmation",
        capture_stage="confirm_params",
        revision=1,
        parameter_values={},
    )

    with pytest.raises(ValidationError, match=f"dataset sourceType is not executable yet: {source_type}"):
        DatasetExecutionService(
            gateway=FixtureExternalBusinessGateway(),
            schema_gateway=ReportDslSchemaGateway(),
        ).resolve(template_instance=instance, user_id="fixture-user")
