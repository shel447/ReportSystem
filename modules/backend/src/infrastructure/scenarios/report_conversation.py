"""把 report context 作为一个强类型业务场景接入通用对话。"""

from __future__ import annotations

from typing import Any

from ...shared.kernel.errors import ValidationError
from ...contexts.conversation.application.scenarios import (
    ScenarioAnswerProjection,
    ScenarioAskProjection,
    ScenarioRegistration,
    ScenarioResult,
)
from ...contexts.conversation.domain.models import ChatContext
from ...contexts.report.application.scenario_models import (
    ReportScenarioCommand,
    report_ask_payload_to_dict,
    report_bootstrap_request_from_dict,
    report_reply_payload_from_dict,
    report_scenario_answer_to_dict,
    report_segment_request_from_dict,
)


class ReportConversationScenarioHandler:
    """执行已经解码为严格 DTO 的报告场景命令。"""

    def __init__(self, *, report_service) -> None:
        self.report_service = report_service

    def handle(self, *, command: object) -> ScenarioResult:
        if not isinstance(command, ReportScenarioCommand):
            raise TypeError("Report scenario handler requires ReportScenarioCommand")
        result = self.report_service.chat(command=command)
        ask = None
        if result.ask is not None:
            ask = ScenarioAskProjection(
                mode=result.ask.mode,
                type=result.ask.type,
                title=result.ask.title,
                text=result.ask.text,
                fields=report_ask_payload_to_dict(result.ask.payload),
            )
        answer = None
        if result.answer is not None:
            answer = ScenarioAnswerProjection(
                answer_type=result.answer.answer_type,
                payload=report_scenario_answer_to_dict(result.answer),
            )
        return ScenarioResult(
            status=result.status,
            ask=ask,
            answer=answer,
            conversation_title=result.conversation_title,
        )


class ReportConversationScenarioCodec:
    """只在系统装配边界把通用入口字段解释为报告命令。"""

    def decode(self, *, context: ChatContext, payload: dict[str, Any]) -> ReportScenarioCommand:
        reply_payload = payload.get("reply") if isinstance(payload.get("reply"), dict) else None
        bootstrap = report_bootstrap_request_from_dict(payload.get("report"))
        if bootstrap is not None and reply_payload is not None:
            raise ValidationError("report cannot be used together with reply")
        return ReportScenarioCommand(
            conversation_id=context.conversation_id,
            chat_id=context.chat_id,
            user_id=context.user_id,
            instruction=str(context.instruction or ""),
            question=context.question,
            reply_type=context.reply_type,
            reply=report_reply_payload_from_dict(reply_payload) if reply_payload is not None else None,
            bootstrap=bootstrap,
            segment=report_segment_request_from_dict(payload.get("template")),
        )


def report_scenario_registration(*, report_service) -> ScenarioRegistration:
    return ScenarioRegistration(
        key="report",
        name="报告生成",
        description="通过多轮对话生成、调整和导出报告",
        instructions={"generate_report", "extract_report_template", "generate_report_segment"},
        default_instruction="generate_report",
        stateless_instructions={"extract_report_template"},
        keywords={"报告", "日报", "周报", "月报", "生成报告"},
        examples={"生成本月网络运行分析报告", "帮我做一份总部网络日报"},
        supports_continuation=True,
        codec=ReportConversationScenarioCodec(),
        handler=ReportConversationScenarioHandler(report_service=report_service),
    )
