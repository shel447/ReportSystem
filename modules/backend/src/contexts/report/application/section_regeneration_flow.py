"""Agent Flow orchestration for report section regeneration."""

from __future__ import annotations

from ....shared.agentflow import FlowGraph, FlowNode, SequentialFlow
from ....shared.kernel.errors import ErrorCode, ValidationError
from .flow_projection import ReportFlowProjection
from .scenario_models import (
    ReportScenarioCommand,
    ReportScenarioAnswer,
    ReportSegmentAnswer,
    report_scenario_answer_to_dict,
)


SECTION_REGENERATION_SUBFLOW_NAME = "report.section_regeneration"


class SectionRegenerationFlowFactory:
    """Build reusable flow graphs for report section regeneration."""

    def __init__(self, *, generation_service, flow_projection: ReportFlowProjection | None = None) -> None:
        self.generation_service = generation_service
        self.flow_projection = flow_projection or ReportFlowProjection()

    def build(self, *, command: ReportScenarioCommand) -> FlowGraph:
        self._validate_command(command)

        def load_context(context) -> None:
            context.emit_step(
                code="report.section_regeneration.load_context",
                title="加载报告与章节上下文",
                status="running",
            )
            context.check_cancelled()
            regeneration_context = self.generation_service.load_section_regeneration_context(
                report_id=command.segment.report_id,
                section_id=command.segment.section_id,
                user_id=command.user_id,
            )
            context.set_state("section_regeneration.context", regeneration_context)
            context.emit_step(
                code="report.section_regeneration.load_context",
                title="加载报告与章节上下文",
                status="finished",
            )

        def locate_section(context) -> None:
            context.emit_step(
                code="report.section_regeneration.locate_section",
                title="定位章节模板",
                status="running",
            )
            context.check_cancelled()
            regeneration_context = context.get_state("section_regeneration.context")
            if regeneration_context is None:
                raise ValidationError("Section regeneration context was not loaded", error_code=ErrorCode.BASE_PARAM_INVALID)
            context.emit_step(
                code="report.section_regeneration.locate_section",
                title="定位章节模板",
                status="finished",
            )

        def apply_outline(context) -> None:
            context.emit_step(
                code="report.section_regeneration.apply_outline",
                title="应用章节大纲",
                status="running",
            )
            context.check_cancelled()
            regeneration_context = context.get_state("section_regeneration.context")
            if regeneration_context is None:
                raise ValidationError("Section regeneration context was not loaded", error_code=ErrorCode.BASE_PARAM_INVALID)
            self.generation_service.apply_section_regeneration_outline(
                context=regeneration_context,
                outline=command.segment.outline,
            )
            context.set_state("section_regeneration.context", regeneration_context)
            context.emit_step(
                code="report.section_regeneration.apply_outline",
                title="应用章节大纲",
                status="finished",
            )

        def compile_section(context) -> None:
            context.emit_step(
                code="report.section_regeneration.compile_section",
                title="生成章节内容",
                status="running",
            )
            context.check_cancelled()
            regeneration_context = context.get_state("section_regeneration.context")
            if regeneration_context is None:
                raise ValidationError("Section regeneration context was not loaded", error_code=ErrorCode.BASE_PARAM_INVALID)
            preview = self.generation_service.compile_section_regeneration(context=regeneration_context)
            answer = {
                "answerType": "REPORT_SEGMENT",
                "answer": report_scenario_answer_to_dict(
                    ReportScenarioAnswer(
                        answer_type="REPORT_SEGMENT",
                        report_segment=ReportSegmentAnswer(
                            report_id=command.segment.report_id,
                            section_id=command.segment.section_id,
                            status="available",
                            section=preview.section,
                            report_meta=preview.report_meta,
                            outline=command.segment.outline,
                        ),
                    )
                ),
            }
            context.set_state("section_regeneration.answer", answer)
            for delta in self.flow_projection.delta_events(answer):
                context.emit_delta(delta)
            context.emit_step(
                code="report.section_regeneration.compile_section",
                title="生成章节内容",
                status="finished",
            )

        def emit_answer(context) -> None:
            context.emit_step(
                code="report.section_regeneration.validate_segment",
                title="校验章节片段",
                status="running",
            )
            context.check_cancelled()
            answer = context.get_state("section_regeneration.answer")
            context.emit_step(
                code="report.section_regeneration.validate_segment",
                title="校验章节片段",
                status="finished",
            )
            context.emit_answer(answer, status="finished")

        return (
            SequentialFlow(
                FlowNode(
                    id="report.section_regeneration.load_context",
                    title="加载报告与章节上下文",
                    handler=load_context,
                    emit_lifecycle_step=False,
                ),
                FlowNode(
                    id="report.section_regeneration.locate_section",
                    title="定位章节模板",
                    handler=locate_section,
                    emit_lifecycle_step=False,
                ),
                FlowNode(
                    id="report.section_regeneration.apply_outline",
                    title="应用章节大纲",
                    handler=apply_outline,
                    emit_lifecycle_step=False,
                ),
                FlowNode(
                    id="report.section_regeneration.compile_section",
                    title="生成章节内容",
                    handler=compile_section,
                    emit_lifecycle_step=False,
                ),
                FlowNode(
                    id="report.section_regeneration.validate_segment",
                    title="校验章节片段",
                    handler=emit_answer,
                    emit_lifecycle_step=False,
                ),
            )
            .to_graph()
        )

    def _validate_command(self, command: ReportScenarioCommand) -> None:
        if (
            command.segment is None
            or not command.segment.report_id.strip()
            or not command.segment.section_id.strip()
            or not str(command.segment.outline.requirement or "").strip()
        ):
            raise ValidationError(
                "generate_report_segment requires template.reportId, template.sectionId and template.outline",
                error_code=ErrorCode.BASE_PARAM_INVALID,
            )
