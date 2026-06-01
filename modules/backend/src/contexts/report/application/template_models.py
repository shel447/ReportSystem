"""模板目录应用层使用的正式输入输出模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..domain.template_models import ParameterValue, ReportTemplate, TemplateSummary, parameter_value_to_dict, report_template_to_dict


@dataclass(slots=True)
class WarningItem:
    """模板导入预览中的结构化提示。"""

    code: str
    message: str
    path: str | None = None
    target_id: str | None = None


@dataclass(slots=True)
class TemplateImportPreview:
    """模板导入预览结果。"""

    normalized_template: ReportTemplate
    warnings: list[WarningItem | str | dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class ParameterOptionsResult:
    """动态参数候选值解析结果。"""

    options: list[ParameterValue] = field(default_factory=list)
    default_value: list[ParameterValue] = field(default_factory=list)


def template_summary_to_dict(summary: TemplateSummary) -> dict[str, object]:
    return {
        "id": summary.id,
        "category": summary.category,
        "name": summary.name,
        "description": summary.description,
        "schemaVersion": summary.schema_version,
        "structureType": summary.structure_type or "flow",
        "updatedAt": summary.updated_at.isoformat().replace("+00:00", "Z") if summary.updated_at else None,
    }


def template_import_preview_to_dict(preview: TemplateImportPreview) -> dict[str, object]:
    return {
        "normalizedTemplate": report_template_to_dict(preview.normalized_template),
        "warnings": [_warning_item_to_dict(item) for item in preview.warnings],
    }


def parameter_options_result_to_dict(result: ParameterOptionsResult) -> dict[str, object]:
    return {
        "options": [parameter_value_to_dict(item) for item in result.options],
        "defaultValue": [parameter_value_to_dict(item) for item in result.default_value],
    }


def _warning_item_to_dict(item: WarningItem | str | dict[str, Any]) -> dict[str, object]:
    if isinstance(item, WarningItem):
        payload: dict[str, object] = {"code": item.code, "message": item.message}
        if item.path:
            payload["path"] = item.path
        if item.target_id:
            payload["targetId"] = item.target_id
        return payload
    if isinstance(item, dict):
        message = str(item.get("message") or item.get("detail") or item)
        payload = {
            "code": str(item.get("code") or "import_warning"),
            "message": message,
        }
        if item.get("path") is not None:
            payload["path"] = str(item.get("path"))
        if item.get("targetId") is not None:
            payload["targetId"] = str(item.get("targetId"))
        return payload
    return {"code": "import_warning", "message": str(item)}
