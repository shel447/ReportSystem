"""报告场景接入通用对话时使用的严格应用层模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeAlias

from ....shared.kernel.errors import ValidationError
from ..domain.generation_models import (
    ReportGenerateMeta,
    ReportSection,
    TemplateInstance,
    report_dsl_from_dict,
    template_instance_from_dict,
    template_instance_to_dict,
)
from ..domain.template_models import (
    OutlineDefinition,
    Parameter,
    outline_definition_from_dict,
    outline_definition_to_dict,
    parameter_from_dict,
    parameter_to_dict,
    report_template_from_dict,
)
from .generation_models import DocumentView, GenerationProgressView, ReportAnswerView
from .generation_models import report_answer_view_to_dict
from .template_models import TemplateImportPreview, template_import_preview_to_dict

Scalar = str | int | float | bool
HistoryTimestamp: TypeAlias = str | int | float | None


@dataclass(slots=True)
class ReportContext:
    """报告场景运行上下文；不属于通用对话上下文。"""

    template_instance: TemplateInstance | None = None


@dataclass(slots=True)
class ReportReplyPayload:
    """报告场景对用户答复的解释结果。"""

    parameters: dict[str, list[Scalar]] = field(default_factory=dict)
    report_context: ReportContext | None = None


@dataclass(slots=True)
class ReportSegmentRequest:
    """报告完成后重新生成单个章节所需的严格输入。"""

    report_id: str
    section_id: str
    outline: OutlineDefinition


@dataclass(slots=True)
class ReportBootstrapParameter:
    """外部系统首次交接的根级参数快照。"""

    parameter: Parameter
    provided_fields: set[str] = field(default_factory=set)


@dataclass(slots=True)
class ReportBootstrapRequest:
    """外部系统已经识别模板并提取部分根级参数后的交接输入。"""

    template_name: str
    parameters: list[ReportBootstrapParameter] = field(default_factory=list)


@dataclass(slots=True)
class ReportHistoryAnswer:
    """历史轮次中按时间排列的一段系统回答。"""

    type: str
    content: str
    answer_time: HistoryTimestamp = None


@dataclass(slots=True)
class ReportHistoryRecord:
    """报告生成可消费的一轮历史对话。"""

    chat_id: str
    question: str
    answers: list[ReportHistoryAnswer] = field(default_factory=list)
    ask_time: HistoryTimestamp = None


@dataclass(slots=True)
class ReportHistoryRequest:
    """基于历史对话生成报告时的严格输入。"""

    structure_type: str = "flow"
    histories: list[ReportHistoryRecord] = field(default_factory=list)


@dataclass(slots=True)
class ReportAskPayload:
    """报告场景附加到通用追问外壳中的业务内容。"""

    parameters: list[Parameter] = field(default_factory=list)
    report_context: ReportContext | None = None


@dataclass(slots=True)
class ReportScenarioCommand:
    """通用对话转交给报告场景的严格命令。"""

    conversation_id: str
    chat_id: str
    user_id: str
    instruction: str
    question: str | None = None
    reply_type: str | None = None
    reply: ReportReplyPayload | None = None
    bootstrap: ReportBootstrapRequest | None = None
    history: ReportHistoryRequest | None = None
    segment: ReportSegmentRequest | None = None


@dataclass(slots=True)
class ReportScenarioAsk:
    """报告场景提出的追问，由 conversation 负责持久化和投影。"""

    mode: str
    type: str
    title: str
    text: str
    payload: ReportAskPayload


@dataclass(slots=True)
class ReportScenarioAnswer:
    """报告场景完成后返回的答案。"""

    answer_type: str
    report: ReportAnswerView | None = None
    report_template_preview: TemplateImportPreview | None = None
    report_segment: "ReportSegmentAnswer | None" = None


@dataclass(slots=True)
class ReportSegmentAnswer:
    """章节重新生成的预览结果。"""

    report_id: str
    section_id: str
    status: str
    section: ReportSection
    report_meta: ReportGenerateMeta
    outline: OutlineDefinition


@dataclass(slots=True)
class ReportScenarioResult:
    """报告场景的一次推进结果。"""

    status: str
    ask: ReportScenarioAsk | None = None
    answer: ReportScenarioAnswer | None = None
    conversation_title: str | None = None


def report_context_from_dict(payload: object) -> ReportContext | None:
    if not isinstance(payload, dict):
        return None
    template_instance_payload = payload.get("templateInstance")
    return ReportContext(
        template_instance=template_instance_from_dict(template_instance_payload)
        if isinstance(template_instance_payload, dict)
        else None
    )


def report_context_to_dict(context: ReportContext | None) -> dict[str, object] | None:
    if context is None:
        return None
    payload: dict[str, object] = {}
    if context.template_instance is not None:
        payload["templateInstance"] = template_instance_to_dict(context.template_instance)
    return payload


def report_ask_payload_from_dict(payload: dict[str, object]) -> ReportAskPayload:
    return ReportAskPayload(
        parameters=[parameter_from_dict(item) for item in list(payload.get("parameters") or [])],
        report_context=report_context_from_dict(payload.get("reportContext")),
    )


def report_ask_payload_to_dict(payload: ReportAskPayload | None) -> dict[str, object]:
    if payload is None:
        return {}
    result: dict[str, object] = {
        "parameters": [parameter_to_dict(item) for item in payload.parameters],
    }
    report_context = report_context_to_dict(payload.report_context)
    if report_context is not None:
        result["reportContext"] = report_context
    return result


def report_reply_payload_from_dict(payload: dict[str, object]) -> ReportReplyPayload:
    return ReportReplyPayload(
        parameters={
            str(key): list(value or [])
            for key, value in dict(payload.get("parameters") or {}).items()
            if isinstance(value, list)
        },
        report_context=report_context_from_dict(payload.get("reportContext")),
    )


def report_segment_request_from_dict(payload: object) -> ReportSegmentRequest | None:
    if not isinstance(payload, dict):
        return None
    outline_payload = payload.get("outline")
    if not isinstance(outline_payload, dict):
        return None
    return ReportSegmentRequest(
        report_id=str(payload.get("reportId") or ""),
        section_id=str(payload.get("sectionId") or ""),
        outline=outline_definition_from_dict(outline_payload),
    )


def report_bootstrap_request_from_dict(payload: object) -> ReportBootstrapRequest | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise ValidationError("report must be an object")
    unexpected_fields = set(payload) - {"templateName", "parameters"}
    if unexpected_fields:
        raise ValidationError(f"report contains unsupported fields: {', '.join(sorted(unexpected_fields))}")
    template_name = str(payload.get("templateName") or "").strip()
    if not template_name:
        raise ValidationError("report.templateName is required")
    raw_parameters = payload.get("parameters", [])
    if not isinstance(raw_parameters, list):
        raise ValidationError("report.parameters must be an array")
    return ReportBootstrapRequest(
        template_name=template_name,
        parameters=[_report_bootstrap_parameter_from_dict(item, index=index) for index, item in enumerate(raw_parameters)],
    )


def report_requests_from_dict(
    report_payload: object,
    histories_payload: object,
) -> tuple[ReportBootstrapRequest | None, ReportHistoryRequest | None]:
    """联合解释 report 与 histories，避免两种报告输入模式互相污染。"""

    histories = _report_histories_from_list(histories_payload)
    if report_payload is not None and not isinstance(report_payload, dict):
        raise ValidationError("report must be an object")

    report_fields = set(report_payload or {})
    supported_fields = {"structureType", "templateName", "parameters"}
    unexpected_fields = report_fields - supported_fields
    if unexpected_fields:
        raise ValidationError(f"report contains unsupported fields: {', '.join(sorted(unexpected_fields))}")

    has_history_option = "structureType" in report_fields
    has_bootstrap_input = bool(report_fields & {"templateName", "parameters"})
    structure_type = str((report_payload or {}).get("structureType") or "").strip()
    if has_history_option and structure_type not in {"flow", "paged"}:
        raise ValidationError("report.structureType must be flow or paged")
    if has_history_option and has_bootstrap_input:
        raise ValidationError("report.structureType cannot be used together with templateName or parameters")

    if histories:
        if has_bootstrap_input:
            raise ValidationError("histories cannot be used together with report.templateName or report.parameters")
        return None, ReportHistoryRequest(
            structure_type=structure_type or "flow",
            histories=histories,
        )

    if has_history_option:
        return None, None
    return report_bootstrap_request_from_dict(report_payload), None


def _report_histories_from_list(payload: object) -> list[ReportHistoryRecord]:
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValidationError("histories must be an array")
    return [_report_history_record_from_dict(item, index=index) for index, item in enumerate(payload)]


def _report_history_record_from_dict(payload: object, *, index: int) -> ReportHistoryRecord:
    if not isinstance(payload, dict):
        raise ValidationError(f"histories[{index}] must be an object")
    chat_id = str(payload.get("chatId") or "").strip()
    question = str(payload.get("question") or "").strip()
    if not chat_id:
        raise ValidationError(f"histories[{index}].chatId is required")
    if not question:
        raise ValidationError(f"histories[{index}].question is required")
    answers_payload = payload.get("answers")
    if not isinstance(answers_payload, list):
        raise ValidationError(f"histories[{index}].answers must be an array")
    ask_time = _history_timestamp(payload.get("askTime"), path=f"histories[{index}].askTime")
    return ReportHistoryRecord(
        chat_id=chat_id,
        question=question,
        ask_time=ask_time,
        answers=[
            _report_history_answer_from_dict(item, record_index=index, answer_index=answer_index)
            for answer_index, item in enumerate(answers_payload)
        ],
    )


def _report_history_answer_from_dict(
    payload: object,
    *,
    record_index: int,
    answer_index: int,
) -> ReportHistoryAnswer:
    path = f"histories[{record_index}].answers[{answer_index}]"
    if not isinstance(payload, dict):
        raise ValidationError(f"{path} must be an object")
    answer_type = str(payload.get("type") or "").strip()
    if answer_type not in {"TEXT", "PIU"}:
        raise ValidationError(f"{path}.type must be TEXT or PIU")
    content = payload.get("content")
    if not isinstance(content, str):
        raise ValidationError(f"{path}.content must be a string")
    return ReportHistoryAnswer(
        type=answer_type,
        content=content,
        answer_time=_history_timestamp(payload.get("answerTime"), path=f"{path}.answerTime"),
    )


def _history_timestamp(value: object, *, path: str) -> HistoryTimestamp:
    if value is None or (isinstance(value, (str, int, float)) and not isinstance(value, bool)):
        return value
    raise ValidationError(f"{path} must be a string or number")


def _report_bootstrap_parameter_from_dict(payload: object, *, index: int) -> ReportBootstrapParameter:
    if not isinstance(payload, dict):
        raise ValidationError(f"report.parameters[{index}] must be an object")
    allowed_fields = {
        "id",
        "label",
        "inputType",
        "required",
        "multi",
        "interactionMode",
        "priority",
        "description",
        "placeholder",
        "defaultValue",
        "options",
        "values",
        "source",
    }
    unexpected_fields = set(payload) - allowed_fields
    if unexpected_fields:
        raise ValidationError(
            f"report.parameters[{index}] contains unsupported fields: {', '.join(sorted(unexpected_fields))}"
        )
    required_fields = {"id", "label", "inputType", "required", "multi", "interactionMode"}
    missing_fields = required_fields - set(payload)
    if missing_fields:
        raise ValidationError(
            f"report.parameters[{index}] requires fields: {', '.join(sorted(missing_fields))}"
        )
    for field_name in ("id", "label", "inputType", "interactionMode"):
        if not isinstance(payload.get(field_name), str) or not str(payload[field_name]).strip():
            raise ValidationError(f"report.parameters[{index}].{field_name} must be a non-empty string")
    if payload["inputType"] not in {"free_text", "date", "enum", "dynamic"}:
        raise ValidationError(f"report.parameters[{index}].inputType is invalid")
    if payload["interactionMode"] not in {"form", "natural_language"}:
        raise ValidationError(f"report.parameters[{index}].interactionMode is invalid")
    for field_name in ("required", "multi"):
        if not isinstance(payload.get(field_name), bool):
            raise ValidationError(f"report.parameters[{index}].{field_name} must be a boolean")
    for field_name in ("source", "description", "placeholder"):
        if field_name in payload and not isinstance(payload[field_name], str):
            raise ValidationError(f"report.parameters[{index}].{field_name} must be a string")
    if "priority" in payload and (
        not isinstance(payload["priority"], int)
        or isinstance(payload["priority"], bool)
        or not 0 <= payload["priority"] <= 99
    ):
        raise ValidationError(f"report.parameters[{index}].priority must be an integer between 0 and 99")
    if str(payload.get("inputType") or "") == "dynamic" and not str(payload.get("source") or "").strip():
        raise ValidationError(f"report.parameters[{index}].source is required for dynamic parameter")
    for field_name in ("options", "defaultValue", "values"):
        if field_name not in payload:
            continue
        values = payload[field_name]
        if not isinstance(values, list) or any(not isinstance(item, dict) for item in values):
            raise ValidationError(f"report.parameters[{index}].{field_name} must be an array of parameter values")
        for value_index, value in enumerate(values):
            _validate_report_bootstrap_parameter_value(value, path=f"report.parameters[{index}].{field_name}[{value_index}]")
    return ReportBootstrapParameter(
        parameter=parameter_from_dict(payload),
        provided_fields=set(payload),
    )


def _validate_report_bootstrap_parameter_value(payload: dict[str, object], *, path: str) -> None:
    if set(payload) != {"label", "value", "query"}:
        raise ValidationError(f"{path} requires exactly label, value and query")
    for field_name in ("label", "value", "query"):
        if not isinstance(payload[field_name], (str, int, float, bool)):
            raise ValidationError(f"{path}.{field_name} must be a scalar")


def report_segment_answer_to_dict(answer: ReportSegmentAnswer) -> dict[str, object]:
    from ..domain.generation_models import report_generate_meta_to_dict, report_section_to_dict

    return {
        "reportId": answer.report_id,
        "sectionId": answer.section_id,
        "status": answer.status,
        "section": report_section_to_dict(answer.section),
        "reportMeta": report_generate_meta_to_dict(answer.report_meta),
        "outline": outline_definition_to_dict(answer.outline),
    }


def report_scenario_answer_to_dict(answer: ReportScenarioAnswer) -> dict[str, object]:
    if answer.report is not None:
        return report_answer_view_to_dict(answer.report)
    if answer.report_template_preview is not None:
        return template_import_preview_to_dict(answer.report_template_preview)
    if answer.report_segment is not None:
        return report_segment_answer_to_dict(answer.report_segment)
    return {}


def report_scenario_answer_from_dict(answer_type: str, payload: dict[str, object]) -> ReportScenarioAnswer:
    """将历史消息中的报告场景答案恢复为严格类型。"""
    answer = ReportScenarioAnswer(answer_type=answer_type)
    if answer_type == "REPORT":
        answer.report = ReportAnswerView(
            report_id=str(payload.get("reportId") or ""),
            status=str(payload.get("status") or ""),
            report=report_dsl_from_dict(payload.get("report") or {}),
            template_instance=template_instance_from_dict(payload.get("templateInstance") or {}),
            documents=[
                DocumentView(
                    id=str(item.get("id") or ""),
                    format=str(item.get("format") or ""),
                    mime_type=str(item.get("mimeType") or ""),
                    file_name=str(item.get("fileName") or ""),
                    download_url=str(item.get("downloadUrl") or ""),
                    status=str(item.get("status") or ""),
                )
                for item in list(payload.get("documents") or [])
                if isinstance(item, dict)
            ],
            generation_progress=GenerationProgressView(
                total_sections=int(((payload.get("generationProgress") or {}).get("totalSections") or 0)),
                completed_sections=int(((payload.get("generationProgress") or {}).get("completedSections") or 0)),
                total_catalogs=int(((payload.get("generationProgress") or {}).get("totalCatalogs") or 0)),
                completed_catalogs=int(((payload.get("generationProgress") or {}).get("completedCatalogs") or 0)),
            )
            if isinstance(payload.get("generationProgress"), dict)
            else None,
        )
    elif answer_type == "REPORT_TEMPLATE":
        answer.report_template_preview = TemplateImportPreview(
            normalized_template=report_template_from_dict(payload.get("normalizedTemplate") or {}),
            warnings=list(payload.get("warnings") or []),
        )
    elif answer_type == "REPORT_SEGMENT":
        from ..domain.generation_models import report_generate_meta_from_dict, report_section_from_dict

        answer.report_segment = ReportSegmentAnswer(
            report_id=str(payload.get("reportId") or ""),
            section_id=str(payload.get("sectionId") or ""),
            status=str(payload.get("status") or ""),
            section=report_section_from_dict(payload.get("section") or {}),
            report_meta=report_generate_meta_from_dict(payload.get("reportMeta") or {}),
            outline=outline_definition_from_dict(payload.get("outline") or {}),
        )
    return answer
