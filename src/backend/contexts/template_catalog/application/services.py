"""静态模板目录及导入导出流程的应用服务。"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from ....shared.kernel.errors import ConflictError, NotFoundError, ValidationError
from ..domain.models import ReportTemplate, TemplateSummary, report_template_from_dict, report_template_to_dict
from .models import TemplateImportPreview


class TemplateCatalogService:
    """负责静态报告模板生命周期的应用服务。"""

    def __init__(self, *, repository, schema_gateway) -> None:
        self.repository = repository
        self.schema_gateway = schema_gateway

    def create_template(self, payload: ReportTemplate) -> ReportTemplate:
        """校验并持久化正式报告模板载荷。"""
        cleaned = self._validate_template_payload(payload)
        try:
            template = self.repository.create(cleaned)
        except ConflictError:
            raise
        return template

    def update_template(self, template_id: str, payload: ReportTemplate) -> ReportTemplate:
        """更新已有模板，同时保持资源标识不可变。"""
        if template_id != str(payload.id or "").strip():
            raise ValidationError("Template id mismatch")
        cleaned = self._validate_template_payload(payload)
        template = self.repository.update(template_id, cleaned)
        return template

    def delete_template(self, template_id: str) -> None:
        self.repository.delete(template_id)

    def get_template(self, template_id: str) -> ReportTemplate:
        """返回接口层与对话匹配流程共同消费的正式模板详情视图。"""
        template = self.repository.get(template_id)
        if template is None:
            raise NotFoundError("Template not found")
        return template

    def list_templates(self) -> list[TemplateSummary]:
        """返回模板列表页使用的紧凑摘要。"""
        return self.repository.list_summaries()

    def export_template(self, template_id: str) -> tuple[ReportTemplate, str]:
        """导出精确的正式模板对象与面向用户的文件名。"""
        template = self.repository.get(template_id)
        if template is None:
            raise NotFoundError("Template not found")
        return template, self._build_export_filename(template)

    def preview_import_template(self, raw_content: Any) -> TemplateImportPreview:
        """解析并校验导入内容，但不修改持久化存储。"""
        normalized = self._parse_import_content(raw_content)
        cleaned = self._validate_template_payload(normalized)
        return TemplateImportPreview(normalized_template=cleaned, warnings=[])

    def _validate_template_payload(self, payload: ReportTemplate) -> ReportTemplate:
        # 校验停留在应用层，这样仓储层只接收结构干净的对象，不需要兼容分支。
        payload_dict = report_template_to_dict(payload)
        try:
            validated = self.schema_gateway.validate(dict(payload_dict or {}))
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        return report_template_from_dict(validated)

    @staticmethod
    def _parse_import_content(raw_content: Any) -> ReportTemplate:
        if isinstance(raw_content, dict):
            return report_template_from_dict(raw_content)
        if isinstance(raw_content, str):
            try:
                loaded = json.loads(raw_content)
            except json.JSONDecodeError as exc:
                raise ValidationError(f"模板导入内容不是合法 JSON: {exc.msg}") from exc
            if not isinstance(loaded, dict):
                raise ValidationError("模板导入内容必须是 JSON 对象")
            return report_template_from_dict(loaded)
        raise ValidationError("模板导入内容必须是对象或 JSON 文本")

    @staticmethod
    def _build_export_filename(template: ReportTemplate) -> str:
        raw_name = str(template.name or "").strip()
        base = re.sub(r'[<>:"/\\\\|?*\x00-\x1f]+', "-", raw_name)
        base = re.sub(r"\s+", "-", base).strip("-.")
        if not base:
            base = template.id
        exported_at = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"{base}-{exported_at}.json"
