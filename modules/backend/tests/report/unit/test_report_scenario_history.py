from types import SimpleNamespace

import pytest

from src.contexts.conversation.domain.models import ScenarioInvocationContext
from src.contexts.report.application.scenario_models import (
    ReportAskPayload,
    ReportScenarioAsk,
    ReportScenarioCommand,
    report_requests_from_dict,
)
from src.contexts.report.application.scenario_service import ReportScenarioService
from src.contexts.report.domain.template_models import report_template_from_dict
from src.contexts.report.infrastructure.scenario_registration import ReportScenarioCodec
from src.shared.kernel.errors import ValidationError


def _template(*, template_id: str, name: str, structure_type: str):
    payload = {
        "id": template_id,
        "category": "project",
        "name": name,
        "description": f"{name}模板",
        "schemaVersion": "template.v3",
        "structureType": structure_type,
        "parameters": [],
    }
    payload["chapters" if structure_type == "paged" else "catalogs"] = []
    return report_template_from_dict(payload)


class _TemplateRepository:
    def __init__(self, templates):
        self.templates = list(templates)

    def list_all(self):
        return list(self.templates)


class _GenerationService:
    def __init__(self, latest=None):
        self.latest = latest
        self.persisted = None

    def get_latest_template_instance(self, *, conversation_id, user_id):
        return self.latest

    def persist_template_instance(self, instance, *, user_id):
        self.persisted = instance
        return instance


class _ParameterService:
    def __init__(self):
        self.extraction_text = None

    def extract_values(self, *, template, question, user_id):
        self.extraction_text = question
        return {}

    def build_ask(self, *, template, template_instance, user_id):
        return ReportScenarioAsk(
            mode="form",
            type="confirm_params",
            title="确认生成条件",
            text="请确认后生成报告。",
            payload=ReportAskPayload(),
        )


def _history_payload():
    return [
        {
            "chatId": "chat_later",
            "question": "第二轮问题",
            "askTime": 20,
            "answers": [
                {"type": "TEXT", "content": "第二轮后回答", "answerTime": 22},
                {"type": "TEXT", "content": "第二轮先回答", "answerTime": 21},
            ],
        },
        {
            "chatId": "chat_earlier",
            "question": "第一轮问题",
            "askTime": 10,
            "answers": [
                {"type": "TEXT", "content": "第一轮回答", "answerTime": 11},
            ],
        },
    ]


def _service(*, templates):
    parameter_service = _ParameterService()
    generation_service = _GenerationService()
    service = ReportScenarioService(
        template_service=SimpleNamespace(),
        template_repository=_TemplateRepository(templates),
        generation_service=generation_service,
        parameter_service=parameter_service,
    )
    return service, parameter_service, generation_service


def test_codec_decodes_non_empty_histories_with_explicit_paged_structure():
    command = ReportScenarioCodec().decode(
        context=ScenarioInvocationContext(
            conversation_id="conv_001",
            chat_id="chat_001",
            user_id="user_001",
            instruction="generate_report",
            scenario_key="report",
            question="请生成项目汇报 PPT",
        ),
        payload={
            "report": {"structureType": "paged"},
            "histories": _history_payload(),
        },
    )

    assert command.bootstrap is None
    assert command.history is not None
    assert command.history.structure_type == "paged"
    assert len(command.history.histories) == 2


def test_history_generation_defaults_to_flow_and_uses_ordered_history_for_matching_and_parameters():
    flow_template = _template(template_id="tpl_flow", name="项目汇报", structure_type="flow")
    paged_template = _template(template_id="tpl_paged", name="项目汇报 PPT", structure_type="paged")
    _, history = report_requests_from_dict(None, _history_payload())
    service, parameter_service, generation_service = _service(templates=[paged_template, flow_template])

    result = service.handle(
        command=ReportScenarioCommand(
            conversation_id="conv_001",
            chat_id="chat_001",
            user_id="user_001",
            instruction="generate_report",
            question="本轮补充要求",
            history=history,
        )
    )

    assert result.status == "waiting_user"
    assert generation_service.persisted.structure_type == "flow"
    assert generation_service.persisted.template_id == "tpl_flow"
    assert parameter_service.extraction_text.splitlines() == [
        "本轮补充要求",
        "第一轮问题",
        "第一轮回答",
        "第二轮问题",
        "第二轮先回答",
        "第二轮后回答",
    ]


def test_history_generation_filters_templates_by_explicit_structure():
    flow_template = _template(template_id="tpl_flow", name="项目汇报 PPT", structure_type="flow")
    paged_template = _template(template_id="tpl_paged", name="普通分页模板", structure_type="paged")
    _, history = report_requests_from_dict({"structureType": "paged"}, _history_payload())
    service, _, generation_service = _service(templates=[flow_template, paged_template])

    service.handle(
        command=ReportScenarioCommand(
            conversation_id="conv_001",
            chat_id="chat_001",
            user_id="user_001",
            instruction="generate_report",
            question="项目汇报 PPT",
            history=history,
        )
    )

    assert generation_service.persisted.structure_type == "paged"
    assert generation_service.persisted.template_id == "tpl_paged"


def test_empty_histories_ignore_structure_type_and_keep_normal_generation_mode():
    bootstrap, history = report_requests_from_dict({"structureType": "paged"}, [])

    assert bootstrap is None
    assert history is None


@pytest.mark.parametrize(
    ("report", "histories"),
    [
        ({"structureType": "slides"}, _history_payload()),
        ({"structureType": "paged", "templateName": "项目汇报"}, _history_payload()),
        ({"templateName": "项目汇报"}, _history_payload()),
    ],
)
def test_history_request_rejects_invalid_or_mixed_report_payload(report, histories):
    with pytest.raises(ValidationError):
        report_requests_from_dict(report, histories)


def test_history_generation_fails_when_requested_structure_has_no_template():
    flow_template = _template(template_id="tpl_flow", name="项目汇报", structure_type="flow")
    _, history = report_requests_from_dict({"structureType": "paged"}, _history_payload())
    service, _, _ = _service(templates=[flow_template])

    with pytest.raises(ValidationError) as error:
        service.handle(
            command=ReportScenarioCommand(
                conversation_id="conv_001",
                chat_id="chat_001",
                user_id="user_001",
                instruction="generate_report",
                question="项目汇报",
                history=history,
            )
        )

    assert error.value.error_code == "chatbi.report.template.not_found"
