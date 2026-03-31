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
    content = normalized.get("content")
    if isinstance(content, dict):
        normalized["content"] = _normalize_content(content)
    subsections = normalized.get("subsections")
    if isinstance(subsections, list):
        normalized["subsections"] = [_normalize_section(item) for item in subsections]
    return normalized


def _normalize_content(content: Dict[str, Any]) -> Dict[str, Any]:
    normalized = copy.deepcopy(content)
    if "datasets" in normalized:
        return normalized

    legacy_source = normalized.pop("source", None)
    if isinstance(legacy_source, dict):
        normalized["datasets"] = [{"id": "ds_main", "source": legacy_source}]
    return normalized


def _format_validation_error(error) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    if path:
        return f"模板定义校验失败: {path} {error.message}"
    return f"模板定义校验失败: {error.message}"
