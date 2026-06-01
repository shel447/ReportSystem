"""报告领域中的参数归一化与作用域解析入口。"""

from __future__ import annotations

import copy
from typing import Any

from .generation_models import TemplateInstanceCatalog, TemplateInstanceChapter
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
        chapters: list[TemplateInstanceChapter] | None = None,
    ) -> list[Parameter]:
        return collect_instance_parameters(parameters=parameters, catalogs=catalogs, chapters=chapters)

    @staticmethod
    def scalar_to_value(raw_value: Any, *, definition: Parameter) -> ParameterValue:
        """把 reply 中的标量解释为模板定义对应的正式参数值。"""
        candidates: list[ParameterValue] = []
        for values in (definition.options, definition.values, definition.default_value):
            candidates.extend(list(values or []))
        for candidate in candidates:
            if raw_value in {candidate.label, candidate.value, candidate.query}:
                return copy.deepcopy(candidate)
        return ParameterValue(label=raw_value, value=raw_value, query=raw_value)

    @staticmethod
    def missing_required(*, template: ReportTemplate, template_instance) -> list[Parameter]:
        values = ParameterResolver.parameters_to_value_map(
            ParameterResolver.collect_instance_parameters(
                parameters=template_instance.parameters,
                catalogs=template_instance.catalogs,
                chapters=template_instance.chapters,
            )
        )
        return [
            parameter
            for parameter in ParameterResolver.collect_template_parameters(template)
            if parameter.required and not list(values.get(parameter.id) or [])
        ]
