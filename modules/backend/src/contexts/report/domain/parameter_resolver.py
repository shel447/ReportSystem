"""报告领域中的参数归一化与作用域解析入口。"""

from __future__ import annotations

from typing import Any

from .generation_models import TemplateInstanceCatalog
from .template_instance_builder import (
    collect_instance_parameters,
    collect_template_parameters,
    merge_parameter_values,
    parameters_by_id,
    parameters_to_value_map,
)
from .template_models import Parameter, ParameterValue, ReportTemplate


class ParameterResolver:
    """集中暴露模板实例构建过程中的纯参数解析能力。"""

    @staticmethod
    def merge_values(
        *,
        parameter_definitions: list[Parameter],
        current_values: dict[str, list[ParameterValue]] | None,
        incoming_values: dict[str, list[ParameterValue]] | None,
    ) -> dict[str, list[ParameterValue]]:
        return merge_parameter_values(
            parameter_definitions=parameter_definitions,
            current_values=current_values,
            incoming_values=incoming_values,
        )

    @staticmethod
    def parameters_to_value_map(parameters: list[Parameter] | None) -> dict[str, list[ParameterValue]]:
        return parameters_to_value_map(parameters)

    @staticmethod
    def parameters_by_id(parameters: list[Parameter] | None) -> dict[str, Parameter]:
        return parameters_by_id(parameters)

    @staticmethod
    def collect_template_parameters(template: ReportTemplate) -> list[Parameter]:
        return collect_template_parameters(template)

    @staticmethod
    def collect_instance_parameters(
        *,
        parameters: list[Parameter] | None,
        catalogs: list[TemplateInstanceCatalog] | None,
    ) -> list[Parameter]:
        return collect_instance_parameters(parameters=parameters, catalogs=catalogs)
