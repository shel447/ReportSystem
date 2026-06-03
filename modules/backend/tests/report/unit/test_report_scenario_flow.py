from src.contexts.conversation.application.scenarios import ScenarioResult
from src.contexts.conversation.domain.models import ChatContext
from src.contexts.report.application.scenario_models import ReportScenarioCommand, ReportScenarioResult
from src.infrastructure.scenarios.report_conversation import ReportConversationScenarioCodec, ReportConversationScenarioHandler
from src.shared.agentflow import FlowGraph, FlowNode, SequentialFlow


class _ReportService:
    def chat_flow(self, *, command: ReportScenarioCommand) -> FlowGraph:
        return SequentialFlow(FlowNode(id="sample", handler=lambda context: context.emit_answer({"answerType": "TEXT", "answer": {}}))).to_graph()

    def chat(self, *, command: ReportScenarioCommand) -> ReportScenarioResult:
        return ReportScenarioResult(status="finished")


def test_generate_report_uses_flow_dispatch():
    handler = ReportConversationScenarioHandler(report_service=_ReportService())
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


def test_extract_template_remains_synchronous():
    handler = ReportConversationScenarioHandler(report_service=_ReportService())
    result = handler.handle(
        command=ReportScenarioCommand(
            conversation_id="",
            chat_id="",
            user_id="u_001",
            instruction="extract_report_template",
            question={},
        )
    )

    assert result.status == "finished"
    assert result.flow is None


def test_report_codec_keeps_strict_command_for_flow():
    command = ReportConversationScenarioCodec().decode(
        context=ChatContext(
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
