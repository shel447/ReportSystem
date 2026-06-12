from __future__ import annotations

import pytest

from src.contexts.report.application.parameter_service import ReportParameterService
from src.contexts.report.domain.generation_models import ParameterConfirmation, TemplateInstance
from src.contexts.report.domain.template_models import Parameter, ParameterValue, ReportTemplate
from src.infrastructure.prompts import get_prompt_catalog
from src.shared.kernel.errors import ErrorCode, ValidationError


class _AiGateway:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def chat_completion(self, _config, messages, **_kwargs):
        prompt = messages[0]["content"]
        self.prompts.append(prompt)
        if "一次性请求上述所有参数" in prompt:
            return {"content": "请同时补充统计日期和分析范围。"}
        if "只请求当前这1个参数" in prompt:
            return {"content": "请补充参数。"}
        raise AssertionError(prompt)


def _parameter(parameter_id: str, *, priority: int) -> Parameter:
    return Parameter(
        id=parameter_id,
        label=parameter_id,
        input_type="free_text",
        required=True,
        multi=False,
        interaction_mode="form",
        priority=priority,
    )


def _template_and_instance():
    parameters = [
        _parameter("reportDate", priority=1),
        _parameter("scope", priority=1),
        _parameter("detail", priority=2),
        _parameter("optionalConfirmOnly", priority=99),
    ]
    template = ReportTemplate(
        id="tpl",
        category="network",
        name="网络报告",
        description="",
        schema_version="template.v3",
        parameters=parameters,
    )
    instance = TemplateInstance(
        id="ti",
        schema_version="template-instance.vNext-draft",
        template_id=template.id,
        template=template,
        conversation_id="conv",
        chat_id="chat",
        status="collecting_parameters",
        capture_stage="fill_params",
        revision=1,
        parameters=parameters,
        parameter_confirmation=ParameterConfirmation(),
    )
    return template, instance


def test_report_parameter_ask_groups_same_priority_and_defers_later_priorities():
    gateway = _AiGateway()
    service = ReportParameterService(
        ai_gateway=gateway,
        completion_config_builder=lambda: object(),
        prompt_catalog=get_prompt_catalog(),
    )
    template, instance = _template_and_instance()

    ask = service.build_ask(template=template, template_instance=instance, user_id="user")

    assert [item.id for item in ask.payload.parameters] == ["reportDate", "scope"]
    assert ask.text == "请同时补充统计日期和分析范围。"
    assert "detail" not in gateway.prompts[0]


def test_priority_99_parameters_are_shown_only_in_confirmation():
    service = ReportParameterService()
    parameters = [_parameter("confirmOnly", priority=99)]
    template = ReportTemplate(
        id="tpl",
        category="network",
        name="网络报告",
        description="",
        schema_version="template.v3",
        parameters=parameters,
    )
    instance = TemplateInstance(
        id="ti",
        schema_version="template-instance.vNext-draft",
        template_id=template.id,
        template=template,
        conversation_id="conv",
        chat_id="chat",
        status="collecting_parameters",
        capture_stage="fill_params",
        revision=1,
        parameters=parameters,
        parameter_confirmation=ParameterConfirmation(),
    )

    ask = service.build_ask(template=template, template_instance=instance)

    assert ask.type == "confirm_params"
    assert [item.id for item in ask.payload.parameters] == ["confirmOnly"]


class _ExtractionAiGateway:
    def __init__(self, content: str) -> None:
        self.content = content

    def chat_completion(self, _config, _messages, **_kwargs):
        return {"content": self.content}


def test_batch_extraction_validates_dates_options_and_multiselect_values():
    template = ReportTemplate(
        id="tpl",
        category="network",
        name="网络报告",
        description="",
        schema_version="template.v3",
        parameters=[
            Parameter(
                id="date",
                label="日期",
                input_type="date",
                required=True,
                multi=False,
                interaction_mode="form",
            ),
            Parameter(
                id="scope",
                label="范围",
                input_type="enum",
                required=True,
                multi=True,
                interaction_mode="form",
                options=[
                    ParameterValue(label="总部", value="hq", query="scope='hq'"),
                    ParameterValue(label="分支", value="branch", query="scope='branch'"),
                ],
            ),
        ],
    )
    service = ReportParameterService(
        ai_gateway=_ExtractionAiGateway('{"date":"2026-06-12","scope":["总部","branch"]}'),
        completion_config_builder=lambda: object(),
        prompt_catalog=get_prompt_catalog(),
    )

    values = service.extract_values(template=template, question="生成报告", user_id="user")

    assert values["date"][0].value == "2026-06-12"
    assert [item.value for item in values["scope"]] == ["hq", "branch"]


def test_batch_extraction_rejects_values_outside_declared_options():
    template = ReportTemplate(
        id="tpl",
        category="network",
        name="网络报告",
        description="",
        schema_version="template.v3",
        parameters=[
            Parameter(
                id="scope",
                label="范围",
                input_type="enum",
                required=True,
                multi=False,
                interaction_mode="form",
                options=[],
            ),
        ],
    )
    service = ReportParameterService(
        ai_gateway=_ExtractionAiGateway('{"scope":"unknown"}'),
        completion_config_builder=lambda: object(),
        prompt_catalog=get_prompt_catalog(),
    )

    with pytest.raises(ValidationError) as exc_info:
        service.extract_values(template=template, question="生成报告", user_id="user")

    assert exc_info.value.error_code == ErrorCode.REPORT_PARAMETER_EXTRACTION_FAILED
