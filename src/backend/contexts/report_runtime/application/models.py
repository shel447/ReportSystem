"""报告运行时应用层的正式输出模型。"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.models import (
    DocumentArtifact,
    ReportDsl,
    TemplateInstance,
    report_dsl_to_dict,
    template_instance_to_dict,
)


@dataclass(slots=True)
class DocumentView:
    """报告文档视图。"""

    id: str
    format: str
    mime_type: str
    file_name: str
    download_url: str
    status: str


@dataclass(slots=True)
class GeneratedArtifact:
    """文档网关返回的生成产物元数据。"""

    file_name: str
    storage_key: str
    mime_type: str


@dataclass(slots=True)
class GenerationProgressView:
    """报告生成进度。"""

    total_sections: int
    completed_sections: int
    total_catalogs: int
    completed_catalogs: int


@dataclass(slots=True)
class ReportAnswerView:
    """聊天与报告详情共用的报告答案视图。"""

    report_id: str
    status: str
    report: ReportDsl
    template_instance: TemplateInstance
    documents: list[DocumentView] = field(default_factory=list)
    generation_progress: GenerationProgressView | None = None


@dataclass(slots=True)
class ReportView:
    """报告详情聚合视图。"""

    report_id: str
    status: str
    answer_type: str
    answer: ReportAnswerView


@dataclass(slots=True)
class DocumentGenerationJobView:
    """单个文档导出任务视图。"""

    job_id: str
    format: str
    status: str
    depends_on: str | None = None


@dataclass(slots=True)
class DocumentGenerationResult:
    """文档生成结果。"""

    report_id: str
    jobs: list[DocumentGenerationJobView] = field(default_factory=list)
    documents: list[DocumentView] = field(default_factory=list)


@dataclass(slots=True)
class DownloadResolution:
    """报告范围下载解析结果。"""

    document: DocumentView
    absolute_path: str


def document_view_from_artifact(document: DocumentArtifact) -> DocumentView:
    return DocumentView(
        id=document.id,
        format=document.artifact_kind,
        mime_type=document.mime_type,
        file_name=document.storage_key.rsplit("\\", 1)[-1].rsplit("/", 1)[-1],
        download_url=f"/rest/chatbi/v1/reports/{document.report_instance_id}/documents/{document.id}/download",
        status=document.status,
    )


def document_view_to_dict(document: DocumentView) -> dict[str, object]:
    return {
        "id": document.id,
        "format": document.format,
        "mimeType": document.mime_type,
        "fileName": document.file_name,
        "downloadUrl": document.download_url,
        "status": document.status,
    }


def generation_progress_to_dict(progress: GenerationProgressView) -> dict[str, int]:
    return {
        "totalSections": progress.total_sections,
        "completedSections": progress.completed_sections,
        "totalCatalogs": progress.total_catalogs,
        "completedCatalogs": progress.completed_catalogs,
    }


def report_answer_view_to_dict(answer: ReportAnswerView) -> dict[str, object]:
    payload: dict[str, object] = {
        "reportId": answer.report_id,
        "status": answer.status,
        "report": report_dsl_to_dict(answer.report),
        "templateInstance": template_instance_to_dict(answer.template_instance),
        "documents": [document_view_to_dict(item) for item in answer.documents],
    }
    if answer.generation_progress is not None:
        payload["generationProgress"] = generation_progress_to_dict(answer.generation_progress)
    return payload


def report_view_to_dict(view: ReportView) -> dict[str, object]:
    return {
        "reportId": view.report_id,
        "status": view.status,
        "answerType": view.answer_type,
        "answer": report_answer_view_to_dict(view.answer),
    }


def document_generation_result_to_dict(result: DocumentGenerationResult) -> dict[str, object]:
    return {
        "reportId": result.report_id,
        "jobs": [
            {
                "jobId": item.job_id,
                "format": item.format,
                "status": item.status,
                "dependsOn": item.depends_on,
            }
            for item in result.jobs
        ],
        "documents": [document_view_to_dict(item) for item in result.documents],
    }
