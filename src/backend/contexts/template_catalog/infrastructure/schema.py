from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict

from jsonschema import Draft7Validator


SCHEMA_VERSION = "v2.0"
_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "report_template_schema_v2.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
_VALIDATOR = Draft7Validator(_SCHEMA)


def normalize_template_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = copy.deepcopy(payload or {})
    parameters = normalized.get("parameters")
    if isinstance(parameters, list):
        normalized["parameters"] = [_normalize_parameter(item) for item in parameters]
    sections = normalized.get("sections")
    if isinstance(sections, list):
        normalized["sections"] = [_normalize_section(item) for item in sections]
    return normalized


def validate_template_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = normalize_template_payload(payload)
    if not _is_v2_candidate(normalized):
        return normalized

    candidate = {
        "id": str(normalized.get("id") or "report_template"),
        "type": str(normalized.get("type") or normalized.get("template_type") or ""),
        "scene": str(normalized.get("scene") or normalized.get("scenario") or ""),
        "name": str(normalized.get("name") or ""),
        "parameters": normalized.get("parameters") or [],
        "sections": normalized.get("sections") or [],
    }
    errors = sorted(_VALIDATOR.iter_errors(candidate), key=lambda item: list(item.path))
    if errors:
        raise ValueError(_format_validation_error(errors[0]))

    _validate_parameter_semantics(normalized.get("parameters") or [])
    normalized["schema_version"] = str(normalized.get("schema_version") or SCHEMA_VERSION)
    return normalized


def _is_v2_candidate(payload: Dict[str, Any]) -> bool:
    return any(
        [
            payload.get("sections"),
            payload.get("parameters"),
            payload.get("type"),
            payload.get("scene"),
            str(payload.get("schema_version") or "").startswith("v2"),
        ]
    )


def _normalize_section(section: Any) -> Any:
    if not isinstance(section, dict):
        return section
    normalized = copy.deepcopy(section)
    outline = normalized.get("outline")
    if isinstance(outline, dict):
        normalized["outline"] = _normalize_outline(outline)
    content = normalized.get("content")
    if isinstance(content, dict):
        normalized["content"] = _normalize_content(content)
    subsections = normalized.get("subsections")
    if isinstance(subsections, list):
        normalized["subsections"] = [_normalize_section(item) for item in subsections]
    return normalized


def _normalize_parameter(parameter: Any) -> Any:
    if not isinstance(parameter, dict):
        return parameter
    normalized = copy.deepcopy(parameter)
    if "options" not in normalized and isinstance(normalized.get("choices"), list):
        normalized["options"] = normalized.pop("choices")
    else:
        normalized.pop("choices", None)
    value_mapping = normalized.get("value_mapping")
    if isinstance(value_mapping, dict):
        query_mapping = value_mapping.get("query")
        if isinstance(query_mapping, dict) and "on_unmapped" not in query_mapping:
            query_mapping["on_unmapped"] = "error"
    return normalized


def _normalize_outline(outline: Dict[str, Any]) -> Dict[str, Any]:
    normalized = copy.deepcopy(outline)
    if "requirement" not in normalized and normalized.get("document") is not None:
        normalized["requirement"] = normalized.pop("document")
    else:
        normalized.pop("document", None)

    if "items" not in normalized:
        if isinstance(normalized.get("slots"), list):
            normalized["items"] = normalized.pop("slots")
        elif isinstance(normalized.get("blocks"), list):
            normalized["items"] = normalized.pop("blocks")
    normalized.pop("slots", None)
    normalized.pop("blocks", None)
    return normalized


def _normalize_content(content: Dict[str, Any]) -> Dict[str, Any]:
    normalized = copy.deepcopy(content)
    if "datasets" in normalized:
        return normalized

    legacy_source = normalized.pop("source", None)
    if isinstance(legacy_source, dict):
        normalized["datasets"] = [{"id": "ds_main", "source": legacy_source}]
    return normalized


def _validate_parameter_semantics(parameters: list[Any]) -> None:
    for index, raw in enumerate(parameters or []):
        if not isinstance(raw, dict):
            continue
        input_type = str(raw.get("input_type") or "").strip()
        value_mode = raw.get("value_mode")
        value_mapping = raw.get("value_mapping")
        options = raw.get("options")

        if input_type not in {"enum", "dynamic"}:
            if value_mode is not None or value_mapping is not None:
                raise ValueError(
                    f"模板定义校验失败: parameters.{index} 仅 enum/dynamic 参数允许声明 value_mode/value_mapping"
                )
            continue

        if input_type == "dynamic" and not str(raw.get("source") or "").strip():
            raise ValueError(f"模板定义校验失败: parameters.{index}.source dynamic 参数必须配置来源")

        if isinstance(options, list):
            for option_index, option in enumerate(options):
                if isinstance(option, str):
                    continue
                if not isinstance(option, dict):
                    raise ValueError(
                        f"模板定义校验失败: parameters.{index}.options.{option_index} 选项只能是字符串或 {{key,label}} 对象"
                    )
                if not str(option.get("key") or "").strip() or not str(option.get("label") or "").strip():
                    raise ValueError(
                        f"模板定义校验失败: parameters.{index}.options.{option_index} 选项对象必须包含非空 key/label"
                    )

        if value_mapping is not None:
            _validate_value_mapping(index, value_mapping)


def _validate_value_mapping(parameter_index: int, value_mapping: Any) -> None:
    if not isinstance(value_mapping, dict):
        raise ValueError(f"模板定义校验失败: parameters.{parameter_index}.value_mapping 必须为对象")
    query_mapping = value_mapping.get("query")
    if not isinstance(query_mapping, dict):
        raise ValueError(f"模板定义校验失败: parameters.{parameter_index}.value_mapping.query 必须为对象")
    by = str(query_mapping.get("by") or "").strip()
    if by not in {"label", "key"}:
        raise ValueError(f"模板定义校验失败: parameters.{parameter_index}.value_mapping.query.by 必须为 label 或 key")
    on_unmapped = str(query_mapping.get("on_unmapped") or "error").strip()
    if on_unmapped != "error":
        raise ValueError(
            f"模板定义校验失败: parameters.{parameter_index}.value_mapping.query.on_unmapped 仅支持 error"
        )
    mapping = query_mapping.get("map")
    if mapping is None:
        return
    if not isinstance(mapping, dict):
        raise ValueError(f"模板定义校验失败: parameters.{parameter_index}.value_mapping.query.map 必须为对象")
    for key, value in mapping.items():
        if not str(key).strip():
            raise ValueError(
                f"模板定义校验失败: parameters.{parameter_index}.value_mapping.query.map 键不能为空"
            )
        if not _is_scalar_or_scalar_list(value):
            raise ValueError(
                f"模板定义校验失败: parameters.{parameter_index}.value_mapping.query.map.{key} 仅支持标量或标量数组"
            )


def _is_scalar_or_scalar_list(value: Any) -> bool:
    if isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(isinstance(item, (str, int, float, bool)) for item in value)
    return False


def _format_validation_error(error) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    if path:
        return f"模板定义校验失败: {path} {error.message}"
    return f"模板定义校验失败: {error.message}"
