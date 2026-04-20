"""模板目录应用层使用的正式输入输出模型。"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.models import ParameterValue, ReportTemplate, TemplateSummary, parameter_value_to_dict, report_template_to_dict


@dataclass(slots=True)
class TemplateImportPreview:
    """模板导入预览结果。"""

    normalized_template: ReportTemplate
    warnings: list[str] = field(default_factory=list)


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
        "updatedAt": summary.updated_at.isoformat().replace("+00:00", "Z") if summary.updated_at else None,
    }


def template_import_preview_to_dict(preview: TemplateImportPreview) -> dict[str, object]:
    return {
        "normalizedTemplate": report_template_to_dict(preview.normalized_template),
        "warnings": list(preview.warnings),
    }


def parameter_options_result_to_dict(result: ParameterOptionsResult) -> dict[str, object]:
    return {
        "options": [parameter_value_to_dict(item) for item in result.options],
        "defaultValue": [parameter_value_to_dict(item) for item in result.default_value],
    }

