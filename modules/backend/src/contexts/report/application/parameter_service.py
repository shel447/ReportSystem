"""报告参数提取、补参和候选值解析应用服务。"""

from __future__ import annotations

import copy
import re
from typing import Any

from ....shared.kernel.errors import ValidationError
from ..domain.generation_models import TemplateInstance
from ..domain.parameter_resolver import ParameterResolver
from ..domain.template_models import Parameter, ParameterValue, ReportTemplate, parameter_value_from_dict
from .scenario_models import ReportAskPayload, ReportContext, ReportScenarioAsk
from .template_models import ParameterOptionsResult
from ..infrastructure.parameter_options import ParameterOptionsGateway
DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


class ReportParameterService:
    """解释报告参数，并通过正式数据源解析动态候选值。"""

    def __init__(self, *, options_gateway: ParameterOptionsGateway | None = None) -> None:
        self.options_gateway = options_gateway or ParameterOptionsGateway()

    def resolve_options(
        self,
        *,
        user_id: str,
        parameter_id: str,
        source: str,
        context_values: dict[str, list[ParameterValue]],
    ) -> ParameterOptionsResult:
        # 动态候选值始终通过统一外部契约解析，对话层只面对一种返回结构。
        request_payload = {
            parameter_id: [{"label": item.label, "value": item.value, "query": item.query} for item in values]
            for parameter_id, values in dict(context_values or {}).items()
        }
        return _to_parameter_options_result(self.options_gateway.resolve(source=source, request_payload=request_payload, user_id=user_id))

    def resolve(
        self,
        *,
        user_id: str,
        parameter_id: str,
        source: str,
        context_values: dict[str, list[ParameterValue]],
    ) -> ParameterOptionsResult:
        """保留内部兼容入口；新调用方使用 resolve_options。"""
        return self.resolve_options(
            user_id=user_id,
            parameter_id=parameter_id,
            source=source,
            context_values=context_values,
        )

    def extract_values(
        self,
        *,
        template: ReportTemplate,
        question: str,
        user_id: str,
    ) -> dict[str, list[ParameterValue]]:
        """按报告参数定义从自然语言中抽取首轮取值。"""
        parameter_values: dict[str, list[ParameterValue]] = {}
        question_text = question or ""
        definitions = ParameterResolver.collect_template_parameters(template)
        for parameter in definitions:
            param_id = str(parameter.id or "").strip()
            input_type = str(parameter.input_type or "")
            matched = None
            if input_type == "date":
                date_match = DATE_PATTERN.search(question_text)
                if date_match:
                    value = date_match.group(0)
                    matched = [ParameterValue(label=value, value=value, query=value)]
            elif input_type == "enum":
                matched = self._match_options(question_text, list(parameter.options or []), multi=parameter.multi)
            elif input_type == "dynamic":
                try:
                    resolved = self.resolve_options(
                        user_id=user_id,
                        parameter_id=param_id,
                        source=str(parameter.source or "").strip(),
                        context_values=parameter_values,
                    )
                except Exception:
                    resolved = None
                matched = self._match_options(
                    question_text,
                    list((resolved.options if resolved is not None else []) or []),
                    multi=parameter.multi,
                )
            elif input_type == "free_text" and question_text.strip():
                matched = [ParameterValue(label=question_text.strip(), value=question_text.strip(), query=question_text.strip())]
            if matched:
                parameter_values[param_id] = matched
        return ParameterResolver.merge_values(
            parameter_definitions=definitions,
            current_values={},
            incoming_values=parameter_values,
        )

    def merge_reply_values(
        self,
        payload: Any,
        *,
        parameter_definitions: list[Parameter],
        current_parameters: list[Parameter] | None,
    ) -> dict[str, list[ParameterValue]]:
        """把场景答复中的标量数组解释为正式参数值。"""
        if not isinstance(payload, dict):
            return {}
        definition_by_id = ParameterResolver.parameters_by_id(parameter_definitions)
        current_by_id = ParameterResolver.parameters_by_id(current_parameters)
        resolved: dict[str, list[ParameterValue]] = {}
        for param_id, raw_values in payload.items():
            normalized_id = str(param_id or "").strip()
            if not normalized_id:
                continue
            definition = current_by_id.get(normalized_id) or definition_by_id.get(normalized_id)
            if definition is None:
                raise ValidationError(f"reply.parameters contains unknown parameter id: {normalized_id}")
            if not isinstance(raw_values, list):
                raise ValidationError(f"reply.parameters.{normalized_id} must be an array")
            resolved[normalized_id] = [ParameterResolver.scalar_to_value(item, definition=definition) for item in raw_values]
        return resolved

    def missing_required_parameters(
        self,
        *,
        template: ReportTemplate,
        template_instance: TemplateInstance,
    ) -> list[Parameter]:
        return ParameterResolver.missing_required(template=template, template_instance=template_instance)

    def build_ask(self, *, template: ReportTemplate, template_instance: TemplateInstance) -> ReportScenarioAsk:
        """构造报告场景的参数补充或确认追问。"""
        missing = self.missing_required_parameters(template=template, template_instance=template_instance)
        if missing:
            next_parameter = missing[0]
            next_state = next(
                (
                    copy.deepcopy(parameter)
                    for parameter in ParameterResolver.collect_instance_parameters(
                        parameters=template_instance.parameters,
                        catalogs=template_instance.catalogs,
                        chapters=template_instance.chapters,
                    )
                    if parameter.id == next_parameter.id
                ),
                copy.deepcopy(next_parameter),
            )
            return ReportScenarioAsk(
                mode="natural_language" if next_parameter.interaction_mode == "natural_language" else "form",
                type="fill_params",
                title="请补充报告参数",
                text=f"请补充参数：{next_parameter.label}",
                payload=ReportAskPayload(
                    parameters=[next_state],
                    report_context=ReportContext(template_instance=template_instance),
                ),
            )
        return ReportScenarioAsk(
            mode="form",
            type="confirm_params",
            title="请确认报告诉求",
            text="请确认报告诉求后开始生成。",
            payload=ReportAskPayload(
                parameters=ParameterResolver.collect_instance_parameters(
                    parameters=template_instance.parameters,
                    catalogs=template_instance.catalogs,
                    chapters=template_instance.chapters,
                ),
                report_context=ReportContext(template_instance=template_instance),
            ),
        )

    @staticmethod
    def _match_options(question: str, options: list[ParameterValue], *, multi: bool) -> list[ParameterValue] | None:
        choices = []
        for option in options:
            label = str(option.label or "")
            value = str(option.value or "")
            if label and label in question or value and value in question:
                choices.append(copy.deepcopy(option))
                if not multi:
                    break
        return choices or None

def _to_parameter_options_result(payload: dict[str, Any]) -> ParameterOptionsResult:
    return ParameterOptionsResult(
        options=[parameter_value_from_dict(item) for item in list(payload.get("options") or [])],
        default_value=[parameter_value_from_dict(item) for item in list(payload.get("defaultValue") or [])],
    )
