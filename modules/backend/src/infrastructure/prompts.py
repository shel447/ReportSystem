"""Backend 提示词资产加载与启动校验。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ..shared.prompts import PromptCatalog, PromptEntry

PROMPT_ROOT = Path(__file__).resolve().parents[2] / "prompts"

PROMPT_FILES = {
    "report_parameter": "report_parameter.yaml",
    "figure": "figure_generate_template.yaml",
    "data_analysis": "data_analysis.yaml",
}

REQUIRED_PROMPTS = {
    "report_parameter.parameter_batch_extract_prompt": {
        "current_time", "user_question", "parameter_definitions", "extract_rule"
    },
    "report_parameter.parameter_extract_prompt": {
        "current_time", "template_name", "current_param_label", "current_question",
        "current_param_options", "extract_rule", "parameter_definitions",
    },
    "report_parameter.parameter_request_prompt": {
        "last_params", "current_param_label", "current_param_type",
        "current_param_required", "current_param_options", "multi_select",
    },
    "report_parameter.parameter_multi_request_prompt": {"last_params", "current_params"},
    "report_parameter.parameter_reask_request_prompt": {
        "value", "current_param_label", "current_param_type",
        "current_param_required", "current_param_options", "multi_select",
    },
    "report_parameter.extract_rule": set(),
    "figure.any": {"user_question", "query_results", "field_descriptions"},
    "figure.text": {"user_question", "query_results", "field_descriptions"},
    "figure.bar": {"user_question", "query_results", "field_descriptions"},
    "figure.line": {"user_question", "query_results", "field_descriptions"},
    "figure.pie": {"user_question", "query_results", "field_descriptions"},
    "figure.ring": {"user_question", "query_results", "field_descriptions"},
    "figure.scatter": {"user_question", "query_results", "field_descriptions"},
    "figure.radar": {"user_question", "query_results", "field_descriptions"},
    "figure.gauge": {"user_question", "query_results", "field_descriptions"},
    "figure.candlestick": {"user_question", "query_results", "field_descriptions"},
    "figure.column_order_system": {"query", "result_fields", "data_sample"},
    "figure.summary_system": {"query", "sql", "result_fields", "data_sample"},
    "figure.rename_column_system": {"query", "sql", "result_fields", "data_sample"},
    "data_analysis.system_prompt": set(),
    "data_analysis.main_template": {
        "THINKING_MODE", "current_dialogue", "ibis_code", "knowledge",
        "similar_queries", "system_time", "table_relation_graph",
    },
}

_catalog: PromptCatalog | None = None


def initialize_prompt_catalog() -> PromptCatalog:
    global _catalog
    entries: dict[str, PromptEntry] = {}
    for namespace, filename in PROMPT_FILES.items():
        payload = _load_yaml(PROMPT_ROOT / filename)
        for key, raw_entry in payload.items():
            if isinstance(raw_entry, str):
                description = f"{key} prompt"
                template = raw_entry
            elif isinstance(raw_entry, dict):
                description = raw_entry.get("description") or f"{key} prompt"
                template = raw_entry.get("prompt")
            else:
                raise ValueError(f"Prompt {namespace}.{key} must be a string or object")
            if not isinstance(template, str) or not template.strip():
                raise ValueError(f"Prompt {namespace}.{key}.prompt is required")
            name = f"{namespace}.{key}"
            entries[name] = PromptEntry(
                name=name,
                description=description.strip(),
                template=template.strip(),
                variables=PromptCatalog.variables(template),
            )
    catalog = PromptCatalog(entries)
    _validate_required_prompts(catalog)
    _catalog = catalog
    return catalog


def get_prompt_catalog() -> PromptCatalog:
    global _catalog
    if _catalog is None:
        _catalog = initialize_prompt_catalog()
    return _catalog


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Prompt file must contain an object: {path}")
    return payload


def _validate_required_prompts(catalog: PromptCatalog) -> None:
    for name, variables in REQUIRED_PROMPTS.items():
        actual = set(catalog.require(name).variables)
        if actual != variables:
            raise ValueError(
                f"Prompt {name} variables mismatch: expected={sorted(variables)}, actual={sorted(actual)}"
            )
