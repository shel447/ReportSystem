"""报告业务在通用对话通道中的场景应用服务。"""

from __future__ import annotations

import copy
import math
import re
from typing import Any

from ....shared.kernel.errors import ValidationError
from ..domain.generation_models import TemplateInstance
from ..domain.generation_services import (
    collect_instance_parameters,
    collect_template_parameters,
    instantiate_template_instance,
    merge_parameter_values,
    parameters_by_id,
    parameters_to_value_map,
)
from ..domain.template_models import Parameter, ParameterValue, ReportTemplate
from .scenario_models import (
    ReportAskPayload,
    ReportContext,
    ReportScenarioAnswer,
    ReportScenarioAsk,
    ReportScenarioCommand,
    ReportScenarioResult,
    ReportSegmentAnswer,
)

DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


class ReportScenarioService:
    """负责报告场景的识别、澄清和生成推进，不管理聊天消息。"""

    def __init__(
        self,
        *,
        template_management_service,
        template_repository,
        runtime_service,
        parameter_option_service,
        ai_gateway=None,
        embedding_config_builder=None,
    ) -> None:
        self.template_management_service = template_management_service
        self.template_repository = template_repository
        self.runtime_service = runtime_service
        self.parameter_option_service = parameter_option_service
        self.ai_gateway = ai_gateway
        self.embedding_config_builder = embedding_config_builder

    def handle(self, *, command: ReportScenarioCommand) -> ReportScenarioResult:
        """按报告 instruction 推进一次场景状态机。"""
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
            answer = self.runtime_service.preview_section_regeneration(
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

    def _extract_report_template(self, *, command: ReportScenarioCommand) -> ReportScenarioResult:
        normalized = self.template_management_service.preview_import_template(command.question or {})
        return ReportScenarioResult(
            status="finished",
            answer=ReportScenarioAnswer(
                answer_type="REPORT_TEMPLATE",
                report_template_preview=normalized,
            ),
        )

    def _generate_report(self, *, command: ReportScenarioCommand) -> ReportScenarioResult:
        reply = command.reply
        current_instance = self.runtime_service.get_latest_template_instance(
            conversation_id=command.conversation_id,
            user_id=command.user_id,
        )

        if command.reply_type == "confirm_params":
            template_instance = reply.report_context.template_instance if reply and reply.report_context else None
            if template_instance is None:
                raise ValidationError("confirm_params requires reportContext.templateInstance")
            template = self.template_management_service.get_template(str(template_instance.template_id or "").strip())
            missing = missing_required_parameters(template=template, template_instance=template_instance)
            if missing:
                missing_ids = ", ".join(item.id for item in missing)
                raise ValidationError(f"confirm_params requires all required parameters: {missing_ids}")
            persisted = self.runtime_service.persist_template_instance(
                _template_instance_from_payload(
                    template_instance,
                    chat_id=command.chat_id,
                    status="confirmed",
                    capture_stage="confirm_params",
                ),
                user_id=command.user_id,
            )
            answer = self.runtime_service.generate_report_from_template_instance(
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
            template = self.template_management_service.get_template(current.template_id)
            definitions = collect_template_parameters(template)
            current_parameters = collect_instance_parameters(parameters=current.parameters, catalogs=current.catalogs)
            merged_values = merge_parameter_values(
                parameter_definitions=definitions,
                current_values=parameters_to_value_map(current_parameters),
                incoming_values=_reply_parameter_values_to_value_map(
                    reply.parameters if reply else None,
                    parameter_definitions=definitions,
                    current_parameters=current_parameters,
                )
                if reply is not None
                else self._extract_parameter_values(template, str(command.question or ""), user_id=command.user_id),
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
            persisted = self.runtime_service.persist_template_instance(instance, user_id=command.user_id)
            return ReportScenarioResult(status="waiting_user", ask=self._build_ask(template=template, template_instance=persisted))

        template = self._match_template(str(command.question or ""))
        initial_values = self._extract_parameter_values(template, str(command.question or ""), user_id=command.user_id)
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
        persisted = self.runtime_service.persist_template_instance(instance, user_id=command.user_id)
        return ReportScenarioResult(
            status="waiting_user",
            ask=self._build_ask(template=template, template_instance=persisted),
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

    def _extract_parameter_values(
        self,
        template: ReportTemplate,
        question: str,
        *,
        user_id: str,
    ) -> dict[str, list[ParameterValue]]:
        """按报告参数定义从自然语言中抽取首轮取值。"""
        parameter_values: dict[str, list[ParameterValue]] = {}
        question_text = question or ""
        for parameter in collect_template_parameters(template):
            param_id = str(parameter.id or "").strip()
            input_type = str(parameter.input_type or "")
            matched = None
            if input_type == "date":
                date_match = DATE_PATTERN.search(question_text)
                if date_match:
                    value = date_match.group(0)
                    matched = [ParameterValue(label=value, value=value, query=value)]
            elif input_type == "enum":
                for option in list(parameter.options or []):
                    label = str(option.label or "")
                    value = str(option.value or "")
                    if label and label in question_text or value and value in question_text:
                        matched = [copy.deepcopy(option)]
                        break
            elif input_type == "dynamic":
                try:
                    resolved = self.parameter_option_service.resolve(
                        user_id=user_id,
                        parameter_id=param_id,
                        source=str(parameter.source or "").strip(),
                        context_values=parameter_values,
                    )
                except Exception:
                    resolved = None
                choices = []
                for option in list((resolved.options if resolved is not None else []) or []):
                    label = str(option.label or "")
                    value = str(option.value or "")
                    if label and label in question_text or value and value in question_text:
                        choices.append(copy.deepcopy(option))
                        if not parameter.multi:
                            break
                if choices:
                    matched = choices
            elif input_type == "free_text" and question_text.strip():
                matched = [ParameterValue(label=question_text.strip(), value=question_text.strip(), query=question_text.strip())]

            if matched:
                parameter_values[param_id] = matched
        return merge_parameter_values(
            parameter_definitions=collect_template_parameters(template),
            current_values={},
            incoming_values=parameter_values,
        )

    def _build_ask(self, *, template: ReportTemplate, template_instance: TemplateInstance) -> ReportScenarioAsk:
        missing = missing_required_parameters(template=template, template_instance=template_instance)
        if missing:
            next_parameter = missing[0]
            next_state = next(
                (
                    copy.deepcopy(parameter)
                    for parameter in collect_instance_parameters(
                        parameters=template_instance.parameters,
                        catalogs=template_instance.catalogs,
                    )
                    if parameter.id == next_parameter.id
                ),
                copy.deepcopy(next_parameter),
            )
            return ReportScenarioAsk(
                mode="natural_language" if next_parameter.interaction_mode == "natural_language" else "form",
                type="fill_params",
                title="请补充报告参数",
                text=f"请补充参数：{next_parameter.label}",
                payload=ReportAskPayload(
                    parameters=[next_state],
                    report_context=ReportContext(template_instance=template_instance),
                ),
            )
        return ReportScenarioAsk(
            mode="form",
            type="confirm_params",
            title="请确认报告诉求",
            text="请确认报告诉求后开始生成。",
            payload=ReportAskPayload(
                parameters=collect_instance_parameters(
                    parameters=template_instance.parameters,
                    catalogs=template_instance.catalogs,
                ),
                report_context=ReportContext(template_instance=template_instance),
            ),
        )


def missing_required_parameters(*, template: ReportTemplate, template_instance: TemplateInstance) -> list[Parameter]:
    values = parameters_to_value_map(
        collect_instance_parameters(
            parameters=template_instance.parameters,
            catalogs=template_instance.catalogs,
        )
    )
    return [
        parameter
        for parameter in collect_template_parameters(template)
        if parameter.required and not list(values.get(parameter.id) or [])
    ]


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


def _reply_parameter_values_to_value_map(
    payload: Any,
    *,
    parameter_definitions: list[Parameter],
    current_parameters: list[Parameter] | None,
) -> dict[str, list[ParameterValue]]:
    if not isinstance(payload, dict):
        return {}
    definition_by_id = parameters_by_id(parameter_definitions)
    current_by_id = parameters_by_id(current_parameters)
    resolved: dict[str, list[ParameterValue]] = {}
    for param_id, raw_values in payload.items():
        normalized_id = str(param_id or "").strip()
        if not normalized_id:
            continue
        definition = current_by_id.get(normalized_id) or definition_by_id.get(normalized_id)
        if definition is None:
            raise ValidationError(f"reply.parameters contains unknown parameter id: {normalized_id}")
        if not isinstance(raw_values, list):
            raise ValidationError(f"reply.parameters.{normalized_id} must be an array")
        resolved[normalized_id] = [_scalar_to_parameter_value(item, definition=definition) for item in raw_values]
    return resolved


def _scalar_to_parameter_value(raw_value: Any, *, definition: Parameter) -> ParameterValue:
    candidates = []
    for values in (definition.options, definition.values, definition.default_value):
        candidates.extend(list(values or []))
    for candidate in candidates:
        if raw_value in {candidate.label, candidate.value, candidate.query}:
            return copy.deepcopy(candidate)
    return ParameterValue(label=raw_value, value=raw_value, query=raw_value)


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
