"""报告参数提取、补参和候选值解析应用服务。"""

from __future__ import annotations

import ast
import copy
from datetime import datetime
import json
import re
from typing import Any

from ....shared.kernel.errors import ApplicationError, ErrorCode, ValidationError
from ....shared.prompts import PromptCatalog
from ..domain.generation_models import (
    TemplateInstance,
    TemplateInstanceCatalog,
    TemplateInstanceChapter,
    TemplateInstanceSection,
    TemplateInstanceSlide,
)
from ..domain.parameter_resolver import ParameterResolver
from ..domain.template_models import Parameter, ParameterValue, ReportTemplate, parameter_value_from_dict
from .interfaces import ParameterOptionsResolver
from .scenario_models import ReportAskPayload, ReportBootstrapRequest, ReportContext, ReportScenarioAsk
from .template_models import ParameterOptionsResult
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NO_PARAMETER_VALUE = "未提取到目标值，请重新输入"


class ReportParameterService:
    """解释报告参数，并通过正式数据源解析动态候选值。"""

    def __init__(
        self,
        *,
        options_gateway: ParameterOptionsResolver | None = None,
        ai_gateway=None,
        completion_config_builder=None,
        prompt_catalog: PromptCatalog | None = None,
    ) -> None:
        self.options_gateway = options_gateway
        self.ai_gateway = ai_gateway
        self.completion_config_builder = completion_config_builder
        self.prompt_catalog = prompt_catalog

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
        if self.options_gateway is None:
            raise ValidationError("dynamic parameter options resolver is not configured")
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
        skip_parameter_ids: set[str] | None = None,
        fixed_option_parameter_ids: set[str] | None = None,
        target_parameter_ids: set[str] | None = None,
        prefer_single_prompt: bool = False,
    ) -> dict[str, list[ParameterValue]]:
        """使用提示词提取参数候选，再按模板定义执行确定性校验。"""
        question_text = str(question or "").strip()
        if not question_text:
            return {}
        skipped = set(skip_parameter_ids or set())
        fixed_options = set(fixed_option_parameter_ids or set())
        targets = set(target_parameter_ids or set())
        definitions = [
            copy.deepcopy(parameter)
            for parameter in ParameterResolver.collect_template_parameters(template)
            if parameter.id not in skipped and (not targets or parameter.id in targets)
        ]
        if not definitions:
            return {}
        self._resolve_dynamic_options_for_definitions(
            definitions=definitions,
            user_id=user_id,
            fixed_option_parameter_ids=fixed_options,
        )
        raw_values = (
            self._extract_single(template=template, parameter=definitions[0], question=question_text)
            if prefer_single_prompt and len(definitions) == 1
            else self._extract_batch(definitions=definitions, question=question_text)
        )
        parameter_values: dict[str, list[ParameterValue]] = {}
        by_id = {parameter.id: parameter for parameter in definitions}
        for parameter_id, raw_value in raw_values.items():
            definition = by_id.get(parameter_id)
            if definition is None:
                raise ValidationError(
                    f"模型返回未知报告参数：{parameter_id}",
                    error_code=ErrorCode.REPORT_PARAMETER_EXTRACTION_FAILED,
                )
            parameter_values[parameter_id] = self._validate_extracted_value(raw_value, definition=definition)
        return ParameterResolver.merge_values(
            parameter_definitions=ParameterResolver.collect_template_parameters(template),
            current_values={},
            incoming_values=parameter_values,
        )

    def merge_bootstrap_values(
        self,
        *,
        template: ReportTemplate,
        bootstrap: ReportBootstrapRequest,
        question: str,
        user_id: str,
    ) -> tuple[ReportTemplate, dict[str, list[ParameterValue]]]:
        """合并外部系统交接的根级参数快照，并补提取尚未赋值的参数。"""
        try:
            merged_template = ParameterResolver.apply_root_parameter_snapshots(
                template=template,
                snapshots=[(item.parameter, item.provided_fields) for item in bootstrap.parameters],
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        external_values = ParameterResolver.parameters_to_value_map(merged_template.parameters)
        fixed_option_parameter_ids = {
            item.parameter.id
            for item in bootstrap.parameters
            if "options" in item.provided_fields
        }
        extracted_values = self.extract_values(
            template=merged_template,
            question=question,
            user_id=user_id,
            skip_parameter_ids=set(external_values),
            fixed_option_parameter_ids=fixed_option_parameter_ids,
        )
        return merged_template, ParameterResolver.merge_values(
            parameter_definitions=ParameterResolver.collect_template_parameters(merged_template),
            current_values=external_values,
            incoming_values=extracted_values,
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

    def build_ask(
        self,
        *,
        template: ReportTemplate,
        template_instance: TemplateInstance,
        user_id: str | None = None,
        reask_value: str | None = None,
    ) -> ReportScenarioAsk:
        """构造报告场景的参数补充或确认追问。"""
        ask_instance = copy.deepcopy(template_instance)
        if user_id:
            self._resolve_dynamic_options_for_instance(template_instance=ask_instance, user_id=user_id)
        missing = self.missing_required_parameters(template=template, template_instance=ask_instance)
        pending = self.next_missing_batch(missing)
        if pending:
            state_by_id = ParameterResolver.parameters_by_id(
                ParameterResolver.collect_instance_parameters(
                    parameters=ask_instance.parameters,
                    catalogs=ask_instance.catalogs,
                    chapters=ask_instance.chapters,
                )
            )
            next_states = [copy.deepcopy(state_by_id.get(item.id) or item) for item in pending]
            text = self._render_parameter_request(
                parameters=next_states,
                template_instance=ask_instance,
                reask_value=reask_value,
            )
            return ReportScenarioAsk(
                mode="natural_language" if all(item.interaction_mode == "natural_language" for item in pending) else "form",
                type="fill_params",
                title="请补充报告参数",
                text=text,
                payload=ReportAskPayload(
                    parameters=next_states,
                    report_context=ReportContext(template_instance=ask_instance),
                ),
            )
        return ReportScenarioAsk(
            mode="form",
            type="confirm_params",
            title="请确认报告诉求",
            text="请确认报告诉求后开始生成。",
            payload=ReportAskPayload(
                parameters=ParameterResolver.collect_instance_parameters(
                    parameters=ask_instance.parameters,
                    catalogs=ask_instance.catalogs,
                    chapters=ask_instance.chapters,
                ),
                report_context=ReportContext(template_instance=ask_instance),
            ),
        )

    @staticmethod
    def next_missing_batch(missing: list[Parameter]) -> list[Parameter]:
        actionable = [parameter for parameter in missing if int(parameter.priority) < 99]
        if not actionable:
            return []
        priority = min(int(parameter.priority) for parameter in actionable)
        return [parameter for parameter in actionable if int(parameter.priority) == priority]

    def _extract_batch(self, *, definitions: list[Parameter], question: str) -> dict[str, Any]:
        content = self._complete(
            "report.parameter.parameter_batch_extract_prompt",
            current_time=datetime.now().isoformat(timespec="seconds"),
            user_question=question,
            parameter_definitions=json.dumps([_parameter_prompt_dict(item) for item in definitions], ensure_ascii=False),
            extract_rule=self._prompt_catalog().render("report.parameter.extract_rule"),
        )
        try:
            payload = json.loads(_strip_code_fence(content))
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "报告参数批量提取结果不是合法 JSON。",
                error_code=ErrorCode.REPORT_PARAMETER_EXTRACTION_FAILED,
            ) from exc
        if not isinstance(payload, dict):
            raise ValidationError(
                "报告参数批量提取结果必须是 JSON object。",
                error_code=ErrorCode.REPORT_PARAMETER_EXTRACTION_FAILED,
            )
        return payload

    def _extract_single(self, *, template: ReportTemplate, parameter: Parameter, question: str) -> dict[str, Any]:
        content = self._complete(
            "report.parameter.parameter_extract_prompt",
            current_time=datetime.now().isoformat(timespec="seconds"),
            template_name=template.name,
            current_param_label=parameter.label,
            current_question=question,
            current_param_options=json.dumps([_parameter_value_dict(item) for item in parameter.options], ensure_ascii=False),
            extract_rule=self._prompt_catalog().render("report.parameter.extract_rule"),
            parameter_definitions=json.dumps(_parameter_prompt_dict(parameter), ensure_ascii=False),
        ).strip()
        if content == NO_PARAMETER_VALUE:
            return {}
        if parameter.multi:
            try:
                value = json.loads(content)
            except ValueError:
                try:
                    value = ast.literal_eval(content)
                except (SyntaxError, ValueError) as exc:
                    raise ValidationError(
                        "报告多选参数提取结果不是合法数组。",
                        error_code=ErrorCode.REPORT_PARAMETER_EXTRACTION_FAILED,
                    ) from exc
        else:
            value = content.strip("\"'")
        return {parameter.id: value}

    def _validate_extracted_value(self, raw_value: Any, *, definition: Parameter) -> list[ParameterValue]:
        values = raw_value if isinstance(raw_value, list) else [raw_value]
        if not definition.multi and len(values) > 1:
            raise ValidationError(
                f"参数“{definition.label}”不支持多选。",
                error_code=ErrorCode.REPORT_PARAMETER_EXTRACTION_FAILED,
            )
        if any(isinstance(value, (dict, list)) or value is None for value in values):
            raise ValidationError(
                f"参数“{definition.label}”提取结果格式无效。",
                error_code=ErrorCode.REPORT_PARAMETER_EXTRACTION_FAILED,
            )
        resolved: list[ParameterValue] = []
        for value in values:
            if definition.input_type == "date" and not DATE_PATTERN.fullmatch(str(value)):
                raise ValidationError(
                    f"参数“{definition.label}”必须使用 YYYY-MM-DD 格式。",
                    error_code=ErrorCode.REPORT_PARAMETER_EXTRACTION_FAILED,
                )
            if definition.input_type in {"enum", "dynamic"}:
                candidate = next(
                    (
                        item for item in definition.options
                        if value in {item.label, item.value, item.query}
                    ),
                    None,
                )
                if candidate is None:
                    raise ValidationError(
                        f"参数“{definition.label}”的值不在候选范围内。",
                        error_code=ErrorCode.REPORT_PARAMETER_EXTRACTION_FAILED,
                    )
                resolved.append(copy.deepcopy(candidate))
            else:
                resolved.append(ParameterResolver.scalar_to_value(value, definition=definition))
        return resolved

    def _resolve_dynamic_options_for_definitions(
        self,
        *,
        definitions: list[Parameter],
        user_id: str,
        fixed_option_parameter_ids: set[str],
    ) -> None:
        context_values: dict[str, list[ParameterValue]] = {}
        for parameter in definitions:
            if parameter.input_type != "dynamic" or parameter.id in fixed_option_parameter_ids or parameter.options:
                continue
            resolved = self.resolve_options(
                user_id=user_id,
                parameter_id=parameter.id,
                source=str(parameter.source or "").strip(),
                context_values=context_values,
            )
            parameter.options = copy.deepcopy(resolved.options)
            parameter.default_value = copy.deepcopy(resolved.default_value)

    def _render_parameter_request(
        self,
        *,
        parameters: list[Parameter],
        template_instance: TemplateInstance,
        reask_value: str | None,
    ) -> str:
        last_params = _filled_parameter_summary(template_instance)
        if len(parameters) > 1:
            return self._complete(
                "report.parameter.parameter_multi_request_prompt",
                last_params=last_params,
                current_params=json.dumps([_parameter_prompt_dict(item) for item in parameters], ensure_ascii=False),
                max_tokens=180,
            ).strip()
        parameter = parameters[0]
        prompt_name = (
            "report.parameter.parameter_reask_request_prompt"
            if reask_value
            else "report.parameter.parameter_request_prompt"
        )
        variables = {
            "current_param_label": parameter.label,
            "current_param_type": parameter.input_type,
            "current_param_required": parameter.required,
            "current_param_options": json.dumps([_parameter_value_dict(item) for item in parameter.options], ensure_ascii=False),
            "multi_select": parameter.multi,
        }
        if reask_value:
            variables["value"] = reask_value
        else:
            variables["last_params"] = last_params
        return self._complete(prompt_name, max_tokens=120, **variables).strip()

    def _complete(self, prompt_name: str, *, max_tokens: int = 800, **variables: Any) -> str:
        if self.ai_gateway is None or self.completion_config_builder is None:
            raise ValidationError(
                "报告参数提示词模型未配置。",
                error_code=ErrorCode.REPORT_PARAMETER_PROMPT_FAILED,
            )
        try:
            response = self.ai_gateway.chat_completion(
                self.completion_config_builder(),
                [{"role": "system", "content": self._prompt_catalog().render(prompt_name, **variables)}],
                temperature=0.0,
                max_tokens=max_tokens,
            )
        except ApplicationError as exc:
            raise ApplicationError(
                "报告参数模型调用失败。",
                details=dict(exc.details),
                error_code=ErrorCode.REPORT_PARAMETER_PROMPT_FAILED,
                category="upstream",
                retryable=exc.retryable,
                source=exc.source,
                http_status=exc.http_status,
            ) from exc
        except Exception as exc:
            raise ApplicationError(
                "报告参数模型调用失败。",
                error_code=ErrorCode.REPORT_PARAMETER_PROMPT_FAILED,
                category="upstream",
                retryable=False,
                http_status=502,
            ) from exc
        content = str(response.get("content") or "").strip()
        if not content:
            raise ValidationError(
                "报告参数提示词没有返回内容。",
                error_code=ErrorCode.REPORT_PARAMETER_PROMPT_FAILED,
            )
        return content

    def _prompt_catalog(self) -> PromptCatalog:
        if self.prompt_catalog is None:
            raise ValidationError(
                "报告参数提示词目录未配置。",
                error_code=ErrorCode.REPORT_PARAMETER_PROMPT_FAILED,
            )
        return self.prompt_catalog

    def _resolve_dynamic_options_for_instance(self, *, template_instance: TemplateInstance, user_id: str) -> None:
        if self.options_gateway is None:
            return
        all_values = ParameterResolver.parameters_to_value_map(
            ParameterResolver.collect_instance_parameters(
                parameters=template_instance.parameters,
                catalogs=template_instance.catalogs,
                chapters=template_instance.chapters,
            )
        )
        for parameter in _iter_instance_parameters(template_instance):
            if parameter.input_type != "dynamic" or not str(parameter.source or "").strip():
                continue
            if parameter.options:
                continue
            try:
                resolved = self.resolve_options(
                    user_id=user_id,
                    parameter_id=parameter.id,
                    source=str(parameter.source or "").strip(),
                    context_values=all_values,
                )
            except Exception:
                continue
            parameter.options = copy.deepcopy(resolved.options)
            if not parameter.default_value:
                parameter.default_value = copy.deepcopy(resolved.default_value)
            if not parameter.values and parameter.default_value:
                parameter.values = copy.deepcopy(parameter.default_value)

def _to_parameter_options_result(payload: dict[str, Any]) -> ParameterOptionsResult:
    return ParameterOptionsResult(
        options=[parameter_value_from_dict(item) for item in list(payload.get("options") or [])],
        default_value=[parameter_value_from_dict(item) for item in list(payload.get("defaultValue") or [])],
    )


def _parameter_value_dict(value: ParameterValue) -> dict[str, Any]:
    return {"label": value.label, "value": value.value, "query": value.query}


def _parameter_prompt_dict(parameter: Parameter) -> dict[str, Any]:
    return {
        "id": parameter.id,
        "label": parameter.label,
        "inputType": parameter.input_type,
        "required": parameter.required,
        "multi": parameter.multi,
        "priority": parameter.priority,
        "description": parameter.description,
        "options": [_parameter_value_dict(item) for item in parameter.options],
    }


def _filled_parameter_summary(template_instance: TemplateInstance) -> str:
    parameters = ParameterResolver.collect_instance_parameters(
        parameters=template_instance.parameters,
        catalogs=template_instance.catalogs,
        chapters=template_instance.chapters,
    )
    values = [
        f"{parameter.label}={','.join(str(item.label) for item in parameter.values)}"
        for parameter in parameters
        if parameter.values
    ]
    return "；".join(values) or "暂无"


def _strip_code_fence(content: str) -> str:
    text = content.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _iter_instance_parameters(template_instance: TemplateInstance):
    yield from template_instance.parameters
    for catalog in template_instance.catalogs:
        yield from _iter_catalog_parameters(catalog)
    for chapter in template_instance.chapters:
        yield from _iter_chapter_parameters(chapter)


def _iter_catalog_parameters(catalog: TemplateInstanceCatalog):
    yield from catalog.parameters
    for section in catalog.sections:
        yield from _iter_section_parameters(section)
    for sub_catalog in catalog.sub_catalogs:
        yield from _iter_catalog_parameters(sub_catalog)


def _iter_chapter_parameters(chapter: TemplateInstanceChapter):
    yield from chapter.parameters
    for slide in chapter.slides:
        yield from _iter_slide_parameters(slide)


def _iter_slide_parameters(slide: TemplateInstanceSlide):
    yield from slide.parameters
    for section in slide.sections:
        yield from _iter_section_parameters(section)


def _iter_section_parameters(section: TemplateInstanceSection):
    yield from section.parameters
