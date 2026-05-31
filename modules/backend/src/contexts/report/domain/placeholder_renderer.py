"""模板实例中的参数和诉求占位符渲染。"""

from __future__ import annotations

import re

from .template_models import ParameterValue, RequirementItem

ITEM_PLACEHOLDER_PATTERN = re.compile(r"\{@([A-Za-z0-9_\-]+)(?:\.(label|value|query))?\}")
PARAMETER_PLACEHOLDER_PATTERN = re.compile(r"\{\$([A-Za-z0-9_\-]+)(?:\.(label|value|query))?\}")


def render_requirement_text(
    template_text: str,
    item_lookup: dict[str, RequirementItem],
    parameter_values: dict[str, list[ParameterValue]],
) -> str:
    rendered = ITEM_PLACEHOLDER_PATTERN.sub(lambda match: _render_item_placeholder(match, item_lookup), template_text)
    rendered = PARAMETER_PLACEHOLDER_PATTERN.sub(lambda match: _render_parameter_placeholder(match, parameter_values), rendered)
    return rendered.strip()


def render_parameter_text(template_text: str, parameter_values: dict[str, list[ParameterValue]]) -> str:
    rendered = PARAMETER_PLACEHOLDER_PATTERN.sub(lambda match: _render_parameter_placeholder(match, parameter_values), template_text)
    return rendered.strip()


def _render_item_placeholder(match: re.Match[str], item_lookup: dict[str, RequirementItem]) -> str:
    item_id = match.group(1)
    channel = match.group(2) or "label"
    item = item_lookup.get(item_id)
    if item is None:
        return ""
    return _render_value_channel(item.values, channel)


def _render_parameter_placeholder(match: re.Match[str], parameter_values: dict[str, list[ParameterValue]]) -> str:
    parameter_id = match.group(1)
    channel = match.group(2) or "label"
    return _render_value_channel(parameter_values.get(parameter_id) or [], channel)


def _render_value_channel(values: list[ParameterValue], channel: str) -> str:
    rendered = [str(getattr(value, channel, None) or value.label or "") for value in values]
    return "、".join([text for text in rendered if text])
