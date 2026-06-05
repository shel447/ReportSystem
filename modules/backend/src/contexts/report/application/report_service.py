"""报告 context 的统一应用入口。"""

from __future__ import annotations

from typing import Any
from ....shared.agentflow import FlowGraph

from ..domain.template_models import ReportTemplate, TemplateSummary
from .document_service import ReportDocumentService
from .generation_models import DocumentGenerationResult, DownloadResolution, ReportView
from .generation_service import ReportGenerationService
from .parameter_service import ReportParameterService
from .scenario_models import ReportScenarioCommand
from .scenario_service import ReportScenarioService
from .template_models import TemplateImportPreview
from .template_service import ReportTemplateService


class ReportService:
    """向 router 和其他 context 暴露稳定的报告应用门面。"""

    def __init__(
        self,
        *,
        scenario_service: ReportScenarioService,
        template_service: ReportTemplateService,
        parameter_service: ReportParameterService,
        generation_service: ReportGenerationService,
        document_service: ReportDocumentService,
    ) -> None:
        self.scenario_service = scenario_service
        self.template_service = template_service
        self.parameter_service = parameter_service
        self.generation_service = generation_service
        self.document_service = document_service

    def chat(self, *, command: ReportScenarioCommand) -> FlowGraph:
        return self.scenario_service.create_flow(command=command)

    def create_template(self, payload: ReportTemplate) -> ReportTemplate:
        return self.template_service.create_template(payload)

    def update_template(self, template_id: str, payload: ReportTemplate) -> ReportTemplate:
        return self.template_service.update_template(template_id, payload)

    def delete_template(self, template_id: str) -> None:
        self.template_service.delete_template(template_id)

    def get_template(self, template_id: str) -> ReportTemplate:
        return self.template_service.get_template(template_id)

    def list_templates(self) -> list[TemplateSummary]:
        return self.template_service.list_templates()

    def export_template(self, template_id: str) -> tuple[ReportTemplate, str]:
        return self.template_service.export_template(template_id)

    def preview_import_template(self, raw_content: Any) -> TemplateImportPreview:
        return self.template_service.preview_import_template(raw_content)

    def get_report_view(self, report_id: str, *, user_id: str) -> ReportView:
        view = self.generation_service.get_report_view(report_id, user_id=user_id)
        view.answer.documents = self.document_service.list_documents(report_id=report_id)
        return view

    def generate_documents(
        self,
        *,
        report_id: str,
        user_id: str,
        formats: list[str],
        pdf_source: str | None,
        theme: str,
        strict_validation: bool,
        regenerate_if_exists: bool,
    ) -> DocumentGenerationResult:
        return self.document_service.generate_documents(
            report_id=report_id,
            user_id=user_id,
            formats=formats,
            pdf_source=pdf_source,
            theme=theme,
            strict_validation=strict_validation,
            regenerate_if_exists=regenerate_if_exists,
        )

    def resolve_download(self, *, report_id: str, document_id: str, user_id: str) -> DownloadResolution:
        return self.document_service.resolve_download(report_id=report_id, document_id=document_id, user_id=user_id)
