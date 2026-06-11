"""报告业务在通用对话通道中的场景应用服务。"""

from __future__ import annotations

import copy
import math

from ....shared.kernel.errors import ConflictError, ErrorCode, ValidationError
from ....shared.agentflow import FlowGraph, FlowNode, SequentialFlow, SubflowSpec
from ..domain.generation_models import TemplateInstance
from ..domain.template_instance_builder import (
    collect_instance_parameters,
    collect_template_parameters,
    instantiate_template_instance,
    merge_parameter_values,
    parameters_to_value_map,
)
from ..domain.template_models import Parameter, ReportTemplate
from ..domain.parameter_resolver import ParameterResolver
from .flow_projection import ReportFlowProjection
from .section_regeneration_flow import SECTION_REGENERATION_SUBFLOW_NAME, SectionRegenerationFlowFactory
from .scenario_models import (
    ReportAskPayload,
    ReportContext,
    ReportHistoryRequest,
    ReportScenarioAnswer,
    ReportScenarioAsk,
    ReportScenarioCommand,
    ReportScenarioResult,
    report_ask_payload_to_dict,
    report_scenario_answer_to_dict,
)

class ReportScenarioService:
    """负责报告场景的识别、澄清和生成推进，不管理聊天消息。"""

    def __init__(
        self,
        *,
        template_service,
        template_repository,
        generation_service,
        parameter_service,
        ai_gateway=None,
        embedding_config_builder=None,
        flow_projection: ReportFlowProjection | None = None,
    ) -> None:
        self.template_service = template_service
        self.template_repository = template_repository
        self.generation_service = generation_service
        self.parameter_service = parameter_service
        self.ai_gateway = ai_gateway
        self.embedding_config_builder = embedding_config_builder
        self.flow_projection = flow_projection or ReportFlowProjection()
        self.section_regeneration_flow = SectionRegenerationFlowFactory(
            generation_service=generation_service,
            flow_projection=self.flow_projection,
        )

    def handle(self, *, command: ReportScenarioCommand) -> ReportScenarioResult:
        """按报告 instruction 推进一次场景状态机。"""
        if command.bootstrap is not None and command.instruction != "generate_report":
            raise ValidationError("report is only supported for generate_report", error_code="chatbi.report.bootstrap.invalid_instruction")
        if command.history is not None and command.instruction != "generate_report":
            raise ValidationError(
                "histories are only supported for generate_report",
                error_code=ErrorCode.BASE_PARAM_INVALID,
            )
        if command.instruction == "extract_report_template":
            return self._extract_report_template(command=command)
        if command.instruction == "generate_report_segment":
            raise ValidationError(
                "generate_report_segment must be executed through report.section_regeneration flow",
                error_code=ErrorCode.BASE_PARAM_INVALID,
            )
        if command.instruction != "generate_report":
            raise ValidationError(f"Unsupported instruction: {command.instruction}", error_code=ErrorCode.BASE_PARAM_INVALID)
        return self._generate_report(command=command)

    def create_flow(self, *, command: ReportScenarioCommand) -> FlowGraph:
        """把报告场景推进封装为公共 Agent Flow。"""
        if command.instruction == "generate_report_segment":
            return self.section_regeneration_flow.build(command=command)

        def run_report(context) -> None:
            if command.instruction == "extract_report_template":
                context.emit_step(code="report.template.preview", title="解析报告模板", status="finished")
            elif command.instruction == "generate_report_segment":
                context.emit_step(code="report.segment.load", title="加载目标章节", status="running")
            elif command.reply_type == "confirm_params":
                context.emit_step(code="report.generate", title="报告生成", status="running")
            else:
                context.emit_step(code="report.template.match", title="识别报告模板", status="finished")
                context.emit_step(code="report.parameters.resolve", title="提取和确认生成条件", status="finished")
            context.check_cancelled()
            result = self.handle(command=command)
            context.check_cancelled()
            if result.ask is not None:
                ask = {
                    "status": "pending",
                    "mode": result.ask.mode,
                    "type": result.ask.type,
                    "title": result.ask.title,
                    "text": result.ask.text,
                }
                ask.update(report_ask_payload_to_dict(result.ask.payload))
                context.emit_ask(ask, status=result.status)
                return
            if result.answer is not None:
                context.emit_step(
                    code="report.dsl.compile",
                    title="编译报告结构",
                    status="finished",
                    parent_step_id="report.generate" if command.reply_type == "confirm_params" else None,
                    step_path=["report.generate", "report.dsl.compile"] if command.reply_type == "confirm_params" else [],
                )
                answer = {
                    "answerType": result.answer.answer_type,
                    "answer": report_scenario_answer_to_dict(result.answer),
                }
                for delta in self.flow_projection.delta_events(answer):
                    context.emit_delta(delta)
                context.emit_answer(answer, status=result.status)
                if command.reply_type == "confirm_params":
                    context.emit_step(code="report.generate", title="报告生成", status="finished")

        return SequentialFlow(
            FlowNode(id="report.generate", title="报告生成", handler=run_report, kind="task", emit_lifecycle_step=False),
        ).to_graph()

    def section_regeneration_subflow_spec(self) -> SubflowSpec:
        """Expose section regeneration as a reusable AgentFlow subflow."""
        return SubflowSpec(
            name=SECTION_REGENERATION_SUBFLOW_NAME,
            build_graph=lambda arguments: self.section_regeneration_flow.build(command=arguments["command"]),
        )

    def _extract_report_template(self, *, command: ReportScenarioCommand) -> ReportScenarioResult:
        normalized = self.template_service.preview_import_template(command.question or {})
        return ReportScenarioResult(
            status="finished",
            answer=ReportScenarioAnswer(
                answer_type="REPORT_TEMPLATE",
                report_template_preview=normalized,
            ),
        )

    def _generate_report(self, *, command: ReportScenarioCommand) -> ReportScenarioResult:
        reply = command.reply
        current_instance = self.generation_service.get_latest_template_instance(
            conversation_id=command.conversation_id,
            user_id=command.user_id,
        )
        if command.bootstrap is not None and current_instance is not None:
            raise ConflictError(
                "report is only supported before a template instance exists",
                error_code="chatbi.report.bootstrap.instance_exists",
            )
        if command.history is not None and current_instance is not None:
            raise ConflictError(
                "histories are only supported before a template instance exists",
                error_code="chatbi.report.history.instance_exists",
            )

        if command.reply_type == "confirm_params":
            template_instance = reply.report_context.template_instance if reply and reply.report_context else None
            if template_instance is None:
                raise ValidationError(
                    "confirm_params requires reportContext.templateInstance",
                    error_code=ErrorCode.BASE_PARAM_INVALID,
                )
            template = self.template_service.get_template(str(template_instance.template_id or "").strip())
            missing = self.parameter_service.missing_required_parameters(template=template, template_instance=template_instance)
            if missing:
                missing_ids = ", ".join(item.id for item in missing)
                raise ValidationError(
                    f"confirm_params requires all required parameters: {missing_ids}",
                    details={"missingParameterIds": [item.id for item in missing]},
                    error_code=ErrorCode.REPORT_PARAMETER_MISSING_REQUIRED,
                )
            persisted = self.generation_service.persist_template_instance(
                _template_instance_from_payload(
                    template_instance,
                    chat_id=command.chat_id,
                    status="confirmed",
                    capture_stage="confirm_params",
                ),
                user_id=command.user_id,
            )
            answer = self.generation_service.generate_report_from_template_instance(
                template_instance_id=persisted.id,
                user_id=command.user_id,
                conversation_id=command.conversation_id,
                chat_id=command.chat_id,
            )
            return ReportScenarioResult(
                status="finished",
                answer=ReportScenarioAnswer(answer_type="REPORT", report=answer),
            )

        if current_instance:
            current = copy.deepcopy(current_instance)
            template = self.template_service.get_template(current.template_id)
            definitions = collect_template_parameters(template)
            current_parameters = collect_instance_parameters(
                parameters=current.parameters,
                catalogs=current.catalogs,
                chapters=current.chapters,
            )
            merged_values = merge_parameter_values(
                parameter_definitions=definitions,
                current_values=parameters_to_value_map(current_parameters),
                incoming_values=self.parameter_service.merge_reply_values(
                    reply.parameters if reply else None,
                    parameter_definitions=definitions,
                    current_parameters=current_parameters,
                )
                if reply is not None
                else self.parameter_service.extract_values(template=template, question=str(command.question or ""), user_id=command.user_id),
            )
            instance = instantiate_template_instance(
                instance_id=current.id,
                template=template,
                conversation_id=command.conversation_id,
                chat_id=command.chat_id,
                status="ready_for_confirmation",
                capture_stage="fill_params",
                revision=int(current.revision or 1) + 1,
                parameter_values=merged_values,
                current_parameters=current_parameters,
                warnings=current.warnings,
                created_at=current.created_at,
            )
            persisted = self.generation_service.persist_template_instance(instance, user_id=command.user_id)
            return ReportScenarioResult(
                status="waiting_user",
                ask=self.parameter_service.build_ask(template=template, template_instance=persisted, user_id=command.user_id),
            )

        if command.bootstrap is not None:
            question = str(command.question or "").strip()
            if not question:
                raise ValidationError("generate_report with report requires question", error_code=ErrorCode.BASE_PARAM_INVALID)
            template = self.template_service.get_template_by_name(command.bootstrap.template_name)
            template, initial_values = self.parameter_service.merge_bootstrap_values(
                template=template,
                bootstrap=command.bootstrap,
                question=question,
                user_id=command.user_id,
            )
        elif command.history is not None:
            generation_text = _history_generation_text(
                question=str(command.question or ""),
                history=command.history,
            )
            template = self._match_template(
                generation_text,
                structure_type=command.history.structure_type,
            )
            initial_values = self.parameter_service.extract_values(
                template=template,
                question=generation_text,
                user_id=command.user_id,
            )
        else:
            template = self._match_template(str(command.question or ""))
            initial_values = self.parameter_service.extract_values(
                template=template,
                question=str(command.question or ""),
                user_id=command.user_id,
            )
        instance = instantiate_template_instance(
            instance_id=_random_id("ti"),
            template=template,
            conversation_id=command.conversation_id,
            chat_id=command.chat_id,
            status="collecting_parameters",
            capture_stage="fill_params",
            revision=1,
            parameter_values=initial_values,
        )
        persisted = self.generation_service.persist_template_instance(instance, user_id=command.user_id)
        return ReportScenarioResult(
            status="waiting_user",
            ask=self.parameter_service.build_ask(template=template, template_instance=persisted, user_id=command.user_id),
            conversation_title=template.name,
        )

    def _match_template(self, question: str, *, structure_type: str | None = None) -> ReportTemplate:
        templates = list(self.template_repository.list_all())
        if structure_type is not None:
            templates = [
                template
                for template in templates
                if str(template.structure_type or "flow") == structure_type
            ]
        if not templates:
            raise ValidationError("No report templates available", error_code=ErrorCode.REPORT_TEMPLATE_NOT_FOUND)
        query_text = question.strip()
        if not query_text:
            return templates[0]

        query_embedding = self._embed_text(query_text)
        scored = []
        for template in templates:
            lexical = _lexical_score(query_text, template)
            semantic = _cosine_similarity(query_embedding, self._embed_text(_template_match_text(template))) if query_embedding else 0.0
            scored.append((lexical + semantic * 0.55, template))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]

    def _embed_text(self, text: str) -> list[float]:
        if not text.strip() or self.ai_gateway is None or self.embedding_config_builder is None:
            return []
        try:
            return self.ai_gateway.create_embedding(self.embedding_config_builder(), [text])[0]
        except Exception:
            return []

def missing_required_parameters(*, template: ReportTemplate, template_instance: TemplateInstance) -> list[Parameter]:
    """兼容旧调用方；新编排通过 ReportParameterService 调用。"""
    return ParameterResolver.missing_required(template=template, template_instance=template_instance)


def _template_instance_from_payload(payload: TemplateInstance, *, chat_id: str, status: str, capture_stage: str) -> TemplateInstance:
    instance = copy.deepcopy(payload)
    instance.chat_id = chat_id
    instance.status = status
    instance.capture_stage = capture_stage
    if capture_stage in {"confirm_params", "generate_report", "report_ready"}:
        instance.parameter_confirmation.missing_parameter_ids = []
        instance.parameter_confirmation.confirmed = True
        instance.parameter_confirmation.confirmed_at = instance.parameter_confirmation.confirmed_at or _iso_timestamp()
    return instance


def _template_match_text(template: ReportTemplate) -> str:
    parts = [str(template.name or ""), str(template.description or ""), str(template.category or "")]
    for parameter in list(template.parameters or []):
        parts.append(str(parameter.label or parameter.id or ""))
    for catalog in list(template.catalogs or []):
        parts.extend(_catalog_match_text(catalog))
    return "\n".join(part for part in parts if part)


def _catalog_match_text(catalog) -> list[str]:
    parts = [str(catalog.title or "")]
    for sub_catalog in list(catalog.sub_catalogs or []):
        parts.extend(_catalog_match_text(sub_catalog))
    for section in list(catalog.sections or []):
        parts.append(str(section.outline.requirement or ""))
    return [part for part in parts if part]


def _lexical_score(question: str, template: ReportTemplate) -> float:
    lowered = question.lower()
    return sum(1.0 for part in [template.name, template.category, template.description] if str(part or "").lower() in lowered and part)


def _history_generation_text(*, question: str, history: ReportHistoryRequest) -> str:
    parts: list[str] = []
    current_question = question.strip()
    if current_question:
        parts.append(current_question)
    ordered_records = sorted(
        enumerate(history.histories),
        key=lambda item: _history_time_sort_key(item[1].ask_time, item[0]),
    )
    for _, record in ordered_records:
        parts.append(record.question)
        ordered_answers = sorted(
            enumerate(record.answers),
            key=lambda item: _history_time_sort_key(item[1].answer_time, item[0]),
        )
        parts.extend(answer.content for _, answer in ordered_answers if answer.content.strip())
    return "\n".join(parts)


def _history_time_sort_key(value: str | int | float | None, index: int) -> tuple[int, float, str, int]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return 0, float(value), "", index
    if isinstance(value, str):
        try:
            return 0, float(value), "", index
        except ValueError:
            return 1, 0.0, value, index
    return 2, 0.0, "", index


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def _random_id(prefix: str) -> str:
    import uuid

    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _iso_timestamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
