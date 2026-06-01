"""报告生成应用服务，负责模板实例持久化、报告冻结和章节预览。"""

from __future__ import annotations

import copy
import uuid

from ....shared.kernel.errors import NotFoundError, ValidationError
from ..domain.generation_models import (
    ReportInstance,
    ReportDsl,
    ReportGenerateMeta,
    ReportSection,
    TemplateInstance,
    report_dsl_to_dict,
    report_section_to_dict,
)
from ..domain.report_dsl_compiler import (
    ReportDslCompiler,
    build_generation_progress,
    find_template_instance_section,
    resource_status_from_dsl,
)
from ..domain.template_instance_builder import build_execution_bindings, serialize_template_instance
from ..domain.template_models import OutlineDefinition, ReportTemplate
from ..infrastructure.template_schema import ReportDslSchemaGateway, validate_template_instance
from .custom_content_resolver import CustomContentResolver
from .generation_models import GenerationProgressView, ReportAnswerView, ReportSegmentPreview, ReportView


class ReportGenerationService:
    """负责模板实例冻结与报告核心视图，不管理文档生命周期。"""

    def __init__(
        self,
        *,
        template_repository,
        template_instance_repository,
        report_instance_repository,
        compiler: ReportDslCompiler | None = None,
        custom_content_resolver: CustomContentResolver | None = None,
        schema_gateway: ReportDslSchemaGateway | None = None,
    ) -> None:
        self.template_repository = template_repository
        self.template_instance_repository = template_instance_repository
        self.report_instance_repository = report_instance_repository
        self.compiler = compiler or ReportDslCompiler()
        self.schema_gateway = schema_gateway or ReportDslSchemaGateway()
        self.custom_content_resolver = custom_content_resolver or CustomContentResolver(schema_gateway=self.schema_gateway)

    def persist_template_instance(self, instance: TemplateInstance, *, user_id: str) -> TemplateInstance:
        try:
            validate_template_instance(serialize_template_instance(instance))
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        existing = self.template_instance_repository.get(instance.id, user_id=user_id)
        return (
            self.template_instance_repository.update(instance, user_id=user_id)
            if existing
            else self.template_instance_repository.create(instance, user_id=user_id)
        )

    def get_latest_template_instance(self, *, conversation_id: str, user_id: str) -> TemplateInstance | None:
        return self.template_instance_repository.get_latest_for_conversation(conversation_id, user_id=user_id)

    def generate_report_from_template_instance(
        self,
        *,
        template_instance_id: str,
        user_id: str,
        conversation_id: str | None,
        chat_id: str | None,
    ) -> ReportAnswerView:
        template_instance = self.template_instance_repository.get(template_instance_id, user_id=user_id)
        if template_instance is None:
            raise NotFoundError("Template instance not found")
        template = self._resolve_template(template_instance)
        report_id = f"rpt_{uuid.uuid4().hex[:12]}"
        custom = self.custom_content_resolver.resolve(template_instance=template_instance)
        report = self.compiler.compile(
            report_id=report_id,
            template=template,
            template_instance=template_instance,
            custom_catalogs=custom.catalogs,
            custom_sections=custom.sections,
        )
        self._validate_report(report)
        instance = self.report_instance_repository.create(
            report_id=report_id,
            template_id=template.id,
            template_instance_id=template_instance.id,
            user_id=user_id,
            conversation_id=conversation_id,
            chat_id=chat_id,
            status=resource_status_from_dsl(report),
            schema_version=report.basic_info.schema_version or "1.0.0",
            report=report,
        )
        template_instance.status = "completed"
        template_instance.capture_stage = "report_ready"
        updated = self.template_instance_repository.update(template_instance, user_id=user_id)
        return self.serialize_report_answer(instance=instance, template_instance=updated)

    def get_report_view(self, report_id: str, *, user_id: str) -> ReportView:
        instance = self.get_report_instance(report_id, user_id=user_id)
        template_instance = self.template_instance_repository.get(instance.template_instance_id, user_id=user_id)
        if template_instance is None:
            raise NotFoundError("Template instance not found")
        return ReportView(
            report_id=instance.id,
            status=instance.status,
            answer_type="REPORT",
            answer=self.serialize_report_answer(instance=instance, template_instance=template_instance),
        )

    def get_report_instance(self, report_id: str, *, user_id: str) -> ReportInstance:
        instance = self.report_instance_repository.get(report_id, user_id=user_id)
        if instance is None:
            raise NotFoundError("Report not found")
        return instance

    def serialize_report_answer(self, *, instance: ReportInstance, template_instance: TemplateInstance) -> ReportAnswerView:
        total_sections, total_catalogs = build_generation_progress(instance.report)
        return ReportAnswerView(
            report_id=instance.id,
            status=instance.status,
            report=instance.report,
            template_instance=template_instance,
            documents=[],
            generation_progress=GenerationProgressView(
                total_sections=total_sections,
                completed_sections=total_sections,
                total_catalogs=total_catalogs,
                completed_catalogs=total_catalogs,
            ),
        )

    def preview_section_regeneration(
        self,
        *,
        report_id: str,
        section_id: str,
        outline: OutlineDefinition,
        user_id: str,
    ) -> ReportSegmentPreview:
        report_instance = self.get_report_instance(report_id, user_id=user_id)
        template_instance = self.template_instance_repository.get(report_instance.template_instance_id, user_id=user_id)
        if template_instance is None:
            raise NotFoundError("Template instance not found")
        section = find_template_instance_section(template_instance.catalogs, section_id)
        if section is None:
            raise NotFoundError("Section not found")
        preview = copy.deepcopy(section)
        preview.outline = copy.deepcopy(outline)
        preview.user_edited = True
        preview.skeleton_status = "reusable"
        preview.runtime_context.bindings = build_execution_bindings(section=preview, item_instances=list(preview.outline.items or []))
        compiled, meta = self.compiler.compile_section(preview)
        try:
            self.schema_gateway.validate_section(report_section_to_dict(compiled))
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        return ReportSegmentPreview(section=compiled, report_meta=meta)

    def _resolve_template(self, template_instance: TemplateInstance) -> ReportTemplate:
        template = copy.deepcopy(template_instance.template)
        if template.id:
            return template
        stored = self.template_repository.get_by_id(template_instance.template_id)
        if stored is None:
            raise NotFoundError("Template not found")
        return copy.deepcopy(stored)

    def _validate_report(self, report: ReportDsl) -> None:
        try:
            self.schema_gateway.validate_report(report_dsl_to_dict(report))
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc


def build_report_dsl(
    *,
    report_id: str,
    template: ReportTemplate,
    template_instance: TemplateInstance,
    custom_content_gateway=None,
) -> ReportDsl:
    """兼容旧内部调用；正式生成链路通过注入的 compiler 与 resolver。"""
    schema_gateway = ReportDslSchemaGateway()
    custom = CustomContentResolver(gateway=custom_content_gateway, schema_gateway=schema_gateway).resolve(template_instance=template_instance)
    return ReportDslCompiler().compile(
        report_id=report_id,
        template=template,
        template_instance=template_instance,
        custom_catalogs=custom.catalogs,
        custom_sections=custom.sections,
    )


def _validate_report_dsl(report: dict) -> None:
    """兼容旧内部测试入口。"""
    try:
        ReportDslSchemaGateway().validate_report(report)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
