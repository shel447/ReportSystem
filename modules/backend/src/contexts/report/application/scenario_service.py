"""报告业务在通用对话通道中的场景应用服务。"""

from __future__ import annotations

import copy
import math

from ....shared.kernel.errors import ConflictError, ValidationError
from ....shared.agentflow import FlowGraph, FlowNode, SequentialFlow
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
from .scenario_models import (
    ReportAskPayload,
    ReportContext,
    ReportScenarioAnswer,
    ReportScenarioAsk,
    ReportScenarioCommand,
    ReportScenarioResult,
    ReportSegmentAnswer,
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
    ) -> None:
        self.template_service = template_service
        self.template_repository = template_repository
        self.generation_service = generation_service
        self.parameter_service = parameter_service
        self.ai_gateway = ai_gateway
        self.embedding_config_builder = embedding_config_builder

    def handle(self, *, command: ReportScenarioCommand) -> ReportScenarioResult:
        """按报告 instruction 推进一次场景状态机。"""
        if command.bootstrap is not None and command.instruction != "generate_report":
            raise ValidationError("report is only supported for generate_report")
        if command.instruction == "extract_report_template":
            return self._extract_report_template(command=command)
        if command.instruction == "generate_report_segment":
            if (
                command.segment is None
                or not command.segment.report_id.strip()
                or not command.segment.section_id.strip()
                or not str(command.segment.outline.requirement or "").strip()
            ):
                raise ValidationError("generate_report_segment requires template.reportId, template.sectionId and template.outline")
            answer = self.generation_service.preview_section_regeneration(
                report_id=command.segment.report_id,
                section_id=command.segment.section_id,
                outline=command.segment.outline,
                user_id=command.user_id,
            )
            return ReportScenarioResult(
                status="finished",
                answer=ReportScenarioAnswer(
                    answer_type="REPORT_SEGMENT",
                    report_segment=ReportSegmentAnswer(
                        report_id=command.segment.report_id,
                        section_id=command.segment.section_id,
                        status="available",
                        section=answer.section,
                        report_meta=answer.report_meta,
                        outline=command.segment.outline,
                    ),
                ),
            )
        if command.instruction != "generate_report":
            raise ValidationError(f"Unsupported instruction: {command.instruction}")
        return self._generate_report(command=command)

    def create_flow(self, *, command: ReportScenarioCommand) -> FlowGraph:
        """把报告场景推进封装为公共 Agent Flow。"""
        if command.instruction == "extract_report_template":
            raise ValidationError("extract_report_template is a stateless synchronous instruction")

        def run_report(context) -> None:
            if command.instruction == "generate_report_segment":
                context.emit_step(code="report.segment.load", title="加载目标章节", status="running")
            else:
                context.emit_step(code="report.template.match", title="识别报告模板", status="running")
                context.emit_step(code="report.parameters.resolve", title="提取和确认生成条件", status="running")
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
                context.emit_step(code="report.dsl.compile", title="编译报告结构", status="finished")
                answer = {
                    "answerType": result.answer.answer_type,
                    "answer": report_scenario_answer_to_dict(result.answer),
                }
                for delta in _report_delta_events(answer):
                    context.emit_delta(delta)
                context.emit_answer(answer, status=result.status)

        return SequentialFlow(
            FlowNode(id="report.generate", title="报告生成", handler=run_report, kind="task"),
        ).to_graph()

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
            raise ConflictError("report is only supported before a template instance exists")

        if command.reply_type == "confirm_params":
            template_instance = reply.report_context.template_instance if reply and reply.report_context else None
            if template_instance is None:
                raise ValidationError("confirm_params requires reportContext.templateInstance")
            template = self.template_service.get_template(str(template_instance.template_id or "").strip())
            missing = self.parameter_service.missing_required_parameters(template=template, template_instance=template_instance)
            if missing:
                missing_ids = ", ".join(item.id for item in missing)
                raise ValidationError(f"confirm_params requires all required parameters: {missing_ids}")
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
            return ReportScenarioResult(status="waiting_user", ask=self.parameter_service.build_ask(template=template, template_instance=persisted))

        if command.bootstrap is not None:
            question = str(command.question or "").strip()
            if not question:
                raise ValidationError("generate_report with report requires question")
            template = self.template_service.get_template_by_name(command.bootstrap.template_name)
            template, initial_values = self.parameter_service.merge_bootstrap_values(
                template=template,
                bootstrap=command.bootstrap,
                question=question,
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
            ask=self.parameter_service.build_ask(template=template, template_instance=persisted),
            conversation_title=template.name,
        )

    def _match_template(self, question: str) -> ReportTemplate:
        templates = list(self.template_repository.list_all())
        if not templates:
            raise ValidationError("No report templates available")
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


def _report_delta_events(answer: dict[str, object]) -> list[dict[str, object]]:
    answer_type = str(answer.get("answerType") or "")
    if answer_type == "REPORT_SEGMENT":
        return [_report_segment_delta_event(answer)]
    if answer_type != "REPORT":
        return []
    report_answer = answer.get("answer") if isinstance(answer.get("answer"), dict) else {}
    report = report_answer.get("report") if isinstance(report_answer.get("report"), dict) else {}
    report_id = str(report_answer.get("reportId") or "")
    basic_info = report.get("basicInfo") if isinstance(report.get("basicInfo"), dict) else {}
    report_title = str(basic_info.get("name") or report_id)
    structure_type = str(report.get("structureType") or "flow")
    deltas: list[dict[str, object]] = [
        {"action": "init_report", "report": {"reportId": report_id, "title": report_title, "structureType": structure_type}},
    ]
    deltas.extend(_catalog_delta_events(list(report.get("catalogs") or []), parent_catalog_id=None, parent_catalog_path=None))
    return deltas


def _report_segment_delta_event(answer: dict[str, object]) -> dict[str, object]:
    segment = answer.get("answer") if isinstance(answer.get("answer"), dict) else {}
    section = segment.get("section") if isinstance(segment.get("section"), dict) else {}
    outline = segment.get("outline") if isinstance(segment.get("outline"), dict) else {}
    return {
        "action": "add_section",
        "structureType": "flow",
        "parent": {"type": "section", "id": str(segment.get("sectionId") or section.get("id") or ""), "path": []},
        "sections": [
            {
                "sectionId": str(segment.get("sectionId") or section.get("id") or ""),
                "status": str(segment.get("status") or "available"),
                "requirement": str(outline.get("renderedRequirement") or outline.get("requirement") or ""),
                "components": list(section.get("components") or []),
            }
        ],
    }


def _catalog_delta_events(
    catalogs: list[dict[str, object]],
    *,
    parent_catalog_id: str | None,
    parent_catalog_path: list[int] | None,
) -> list[dict[str, object]]:
    deltas: list[dict[str, object]] = []
    if catalogs:
        deltas.append(
            {
                "action": "add_catalog",
                "structureType": "flow",
                "parentCatalogId": parent_catalog_id,
                "parentCatalog": parent_catalog_path,
                "parent": {
                    "type": "report" if parent_catalog_id is None else "catalog",
                    "id": parent_catalog_id,
                    "path": parent_catalog_path,
                },
                "catalogs": [
                    {
                        "catalogId": str(catalog.get("id") or ""),
                        "title": str(catalog.get("name") or catalog.get("title") or catalog.get("id") or ""),
                    }
                    for catalog in catalogs
                ],
            }
        )
    for index, catalog in enumerate(catalogs):
        catalog_path = [*parent_catalog_path, index] if parent_catalog_path is not None else [index]
        sections = list(catalog.get("sections") or [])
        if sections:
            deltas.append(
                {
                    "action": "add_section",
                    "structureType": "flow",
                    "parentCatalogId": str(catalog.get("id") or ""),
                    "parentCatalog": catalog_path,
                    "parent": {"type": "catalog", "id": str(catalog.get("id") or ""), "path": catalog_path},
                    "sections": [
                        {
                            "sectionId": str(section.get("id") or ""),
                            "status": "finished",
                            "requirement": str(section.get("title") or section.get("requirement") or section.get("id") or ""),
                            "components": list(section.get("components") or []),
                        }
                        for section in sections
                    ],
                }
            )
        deltas.extend(
            _catalog_delta_events(
                list(catalog.get("subCatalogs") or []),
                parent_catalog_id=str(catalog.get("id") or ""),
                parent_catalog_path=catalog_path,
            )
        )
    return deltas
