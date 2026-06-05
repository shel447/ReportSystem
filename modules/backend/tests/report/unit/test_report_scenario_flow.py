from src.contexts.conversation.application.scenarios import ScenarioResult
from src.contexts.conversation.domain.models import ScenarioInvocationContext
from src.contexts.report.application.scenario_models import ReportScenarioCommand
from src.contexts.report.infrastructure.scenario_registration import ReportScenarioCodec, ReportScenarioHandler
from src.shared.agentflow import FlowGraph, FlowNode, SequentialFlow


class _ReportService:
    def chat(self, *, command: ReportScenarioCommand) -> FlowGraph:
        return SequentialFlow(FlowNode(id="sample", handler=lambda context: context.emit_answer({"answerType": "TEXT", "answer": {}}))).to_graph()


def test_generate_report_uses_flow_dispatch():
    handler = ReportScenarioHandler(report_service=_ReportService())
    result = handler.handle(
        command=ReportScenarioCommand(
            conversation_id="conv_001",
            chat_id="chat_001",
            user_id="u_001",
            instruction="generate_report",
            question="生成日报",
        )
    )

    assert isinstance(result, ScenarioResult)
    assert result.status == "running"
    assert result.flow is not None


def test_extract_template_uses_unified_flow_entry():
    handler = ReportScenarioHandler(report_service=_ReportService())
    result = handler.handle(
        command=ReportScenarioCommand(
            conversation_id="",
            chat_id="",
            user_id="u_001",
            instruction="extract_report_template",
            question={},
        )
    )

    assert result.status == "running"
    assert result.flow is not None


def test_report_codec_keeps_strict_command_for_flow():
    command = ReportScenarioCodec().decode(
        context=ScenarioInvocationContext(
            conversation_id="conv_001",
            chat_id="chat_001",
            user_id="u_001",
            instruction="generate_report",
            scenario_key="report",
            question="生成日报",
        ),
        payload={"instruction": "generate_report", "question": "生成日报"},
    )

    assert isinstance(command, ReportScenarioCommand)
    assert command.conversation_id == "conv_001"
    assert command.instruction == "generate_report"
