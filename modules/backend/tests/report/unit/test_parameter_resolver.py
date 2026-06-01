from src.contexts.report.domain.generation_models import ParameterConfirmation, TemplateInstance
from src.contexts.report.domain.parameter_resolver import ParameterResolver
from src.contexts.report.domain.template_models import Parameter, ParameterValue, ReportTemplate


def test_parameter_resolver_maps_known_scalar_to_declared_value():
    declared = ParameterValue(label="总部网络", value="hq-network", query="scope_id = 'hq-network'")
    resolved = ParameterResolver.scalar_to_value(
        "hq-network",
        definition=Parameter(
            id="scope",
            label="范围",
            input_type="enum",
            required=True,
            multi=False,
            interaction_mode="form",
            options=[declared],
        ),
    )
    assert resolved == declared
    assert resolved is not declared


def test_parameter_resolver_finds_missing_required_parameter():
    template = ReportTemplate(
        id="tpl_001",
        category="network",
        name="日报",
        description="",
        schema_version="template.v3",
        parameters=[
            Parameter(
                id="scope",
                label="范围",
                input_type="free_text",
                required=True,
                multi=False,
                interaction_mode="form",
            )
        ],
    )
    instance = TemplateInstance(
        id="ti_001",
        schema_version="template-instance.vNext-draft",
        template_id=template.id,
        template=template,
        conversation_id="conv_001",
        chat_id=None,
        status="collecting_parameters",
        capture_stage="fill_params",
        revision=1,
        parameter_confirmation=ParameterConfirmation(),
    )
    assert [item.id for item in ParameterResolver.missing_required(template=template, template_instance=instance)] == ["scope"]
