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
    def apply_root_parameter_snapshots(
        *,
        template: ReportTemplate,
        snapshots: list[tuple[Parameter, set[str]]],
    ) -> ReportTemplate:
        """校验并应用外部系统首次交接的根级参数快照。"""
        merged_template = copy.deepcopy(template)
        root_by_id = {item.id.strip(): item for item in merged_template.parameters if item.id.strip()}
        all_ids = {item.id.strip() for item in collect_template_parameters(merged_template) if item.id.strip()}
        seen_ids: set[str] = set()
        for snapshot, provided_fields in snapshots:
            parameter_id = snapshot.id.strip()
            if not parameter_id:
                raise ValueError("report.parameters[].id is required")
            if parameter_id in seen_ids:
                raise ValueError(f"report.parameters contains duplicate parameter id: {parameter_id}")
            seen_ids.add(parameter_id)
            definition = root_by_id.get(parameter_id)
            if definition is None:
                if parameter_id in all_ids:
                    raise ValueError(f"report.parameters only supports root-level parameter: {parameter_id}")
                raise ValueError(f"report.parameters contains unknown parameter id: {parameter_id}")
            ParameterResolver._validate_snapshot_definition(
                definition=definition,
                snapshot=snapshot,
                provided_fields=provided_fields,
            )
            if "options" in provided_fields:
                definition.options = copy.deepcopy(snapshot.options)
            if "defaultValue" in provided_fields:
                definition.default_value = copy.deepcopy(snapshot.default_value)
            if "values" in provided_fields:
                definition.values = copy.deepcopy(snapshot.values)
            ParameterResolver._validate_snapshot_values(definition=definition)
        return merged_template

    @staticmethod
    def _validate_snapshot_definition(
        *,
        definition: Parameter,
        snapshot: Parameter,
        provided_fields: set[str],
    ) -> None:
        required_fields = {
            "label": "label",
            "inputType": "input_type",
            "required": "required",
            "multi": "multi",
            "interactionMode": "interaction_mode",
        }
        optional_fields = {
            "source": "source",
            "priority": "priority",
            "description": "description",
            "placeholder": "placeholder",
        }
        for public_name, attribute_name in required_fields.items():
            if getattr(snapshot, attribute_name) != getattr(definition, attribute_name):
                raise ValueError(f"report.parameters.{definition.id}.{public_name} conflicts with template")
        for public_name, attribute_name in optional_fields.items():
            if public_name in provided_fields and getattr(snapshot, attribute_name) != getattr(definition, attribute_name):
                raise ValueError(f"report.parameters.{definition.id}.{public_name} conflicts with template")

    @staticmethod
    def _validate_snapshot_values(*, definition: Parameter) -> None:
        if not definition.multi:
            for field_name, values in (("defaultValue", definition.default_value), ("values", definition.values)):
                if len(values) > 1:
                    raise ValueError(f"report.parameters.{definition.id}.{field_name} exceeds single-value constraint")
        if definition.input_type not in {"enum", "dynamic"}:
            return
        option_by_value = {item.value: item for item in definition.options}
        for attribute_name, public_name in (("default_value", "defaultValue"), ("values", "values")):
            values = getattr(definition, attribute_name)
            canonical_values: list[ParameterValue] = []
            for value in values:
                option = option_by_value.get(value.value)
                if option is None:
                    raise ValueError(
                        f"report.parameters.{definition.id}.{public_name} contains value outside options: {value.value}"
                    )
                canonical_values.append(copy.deepcopy(option))
            setattr(definition, attribute_name, canonical_values)

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
