"""唯一报告模板定义契约的结构校验辅助函数。"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, RefResolver


DESIGN_ROOT = Path(__file__).resolve().parents[5] / "design" / "report_system"
TEMPLATE_SCHEMA_PATH = DESIGN_ROOT / "schemas" / "report-template.schema.json"
TEMPLATE_INSTANCE_SCHEMA_PATH = DESIGN_ROOT / "schemas" / "template-instance.schema.json"
PARAMETER_OPTION_REQUEST_SCHEMA_PATH = DESIGN_ROOT / "schemas" / "parameter-option-source-request.schema.json"
PARAMETER_OPTION_RESPONSE_SCHEMA_PATH = DESIGN_ROOT / "schemas" / "parameter-option-source-response.schema.json"


def _read_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


_TEMPLATE_SCHEMA = _read_schema(TEMPLATE_SCHEMA_PATH)
_TEMPLATE_INSTANCE_SCHEMA = _read_schema(TEMPLATE_INSTANCE_SCHEMA_PATH)
_PARAMETER_OPTION_RESPONSE_SCHEMA = _read_schema(PARAMETER_OPTION_RESPONSE_SCHEMA_PATH)

_TEMPLATE_VALIDATOR = Draft202012Validator(_TEMPLATE_SCHEMA)
_PARAMETER_OPTION_STORE = {
    TEMPLATE_SCHEMA_PATH.name: _TEMPLATE_SCHEMA,
    f"./{TEMPLATE_SCHEMA_PATH.name}": _TEMPLATE_SCHEMA,
    TEMPLATE_SCHEMA_PATH.as_uri(): _TEMPLATE_SCHEMA,
    TEMPLATE_INSTANCE_SCHEMA_PATH.name: _TEMPLATE_INSTANCE_SCHEMA,
    f"./{TEMPLATE_INSTANCE_SCHEMA_PATH.name}": _TEMPLATE_INSTANCE_SCHEMA,
    TEMPLATE_INSTANCE_SCHEMA_PATH.as_uri(): _TEMPLATE_INSTANCE_SCHEMA,
}
_TEMPLATE_INSTANCE_VALIDATOR = Draft202012Validator(
    _TEMPLATE_INSTANCE_SCHEMA,
    resolver=RefResolver(
        base_uri=TEMPLATE_INSTANCE_SCHEMA_PATH.parent.as_uri() + "/",
        referrer=_TEMPLATE_INSTANCE_SCHEMA,
        store=_PARAMETER_OPTION_STORE,
    ),
)
_PARAMETER_OPTION_RESPONSE_VALIDATOR = Draft202012Validator(
    _PARAMETER_OPTION_RESPONSE_SCHEMA,
    resolver=RefResolver(
        base_uri=PARAMETER_OPTION_RESPONSE_SCHEMA_PATH.parent.as_uri() + "/",
        referrer=_PARAMETER_OPTION_RESPONSE_SCHEMA,
        store=_PARAMETER_OPTION_STORE,
    ),
)


def validate_report_template(payload: dict[str, Any]) -> dict[str, Any]:
    """校验设计资料包定义的正式报告模板契约。"""
    candidate = copy.deepcopy(payload or {})
    _raise_first_error(_TEMPLATE_VALIDATOR, candidate, "模板定义校验失败")
    return candidate


def validate_template_instance(payload: dict[str, Any]) -> dict[str, Any]:
    """按设计原样校验运行时模板实例契约。"""
    candidate = copy.deepcopy(payload or {})
    _raise_first_error(_TEMPLATE_INSTANCE_VALIDATOR, candidate, "模板实例校验失败")
    return candidate


def validate_parameter_option_source_response(payload: dict[str, Any]) -> dict[str, Any]:
    """先归一化可选字段，再校验动态选项响应契约。"""
    candidate = copy.deepcopy(payload or {})
    options = candidate.get("options")
    default_value = candidate.get("defaultValue")
    if options is None:
        candidate["options"] = []
    if default_value is None:
        candidate["defaultValue"] = []
    _raise_first_error(_PARAMETER_OPTION_RESPONSE_VALIDATOR, candidate, "动态参数数据源响应校验失败")
    return candidate


def _raise_first_error(validator: Draft202012Validator, payload: dict[str, Any], prefix: str) -> None:
    # 只暴露第一条错误，这样接口返回的是单一、明确的契约失败，
    # 不会把校验器内部细节泄漏到路由层。
    errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
    if not errors:
        return
    error = errors[0]
    path = ".".join(str(part) for part in error.absolute_path)
    if path:
        raise ValueError(f"{prefix}: {path} {error.message}")
    raise ValueError(f"{prefix}: {error.message}")
