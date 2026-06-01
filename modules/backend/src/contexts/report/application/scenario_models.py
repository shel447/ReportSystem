"""报告场景接入通用对话时使用的严格应用层模型。"""

from __future__ import annotations

from dataclasses import dataclass, field

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
            warnings=[str(item) for item in list(payload.get("warnings") or [])],
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
