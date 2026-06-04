"""唯一报告模板定义契约的结构校验辅助函数。"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, RefResolver

from src.shared.kernel.paths import project_root


CONTRACTS_ROOT = project_root() / "docs" / "implementation" / "contracts"
TEMPLATE_SCHEMA_PATH = CONTRACTS_ROOT / "schemas" / "report-template.schema.json"
TEMPLATE_INSTANCE_SCHEMA_PATH = CONTRACTS_ROOT / "schemas" / "template-instance.schema.json"
PARAMETER_OPTION_REQUEST_SCHEMA_PATH = CONTRACTS_ROOT / "schemas" / "parameter-option-source-request.schema.json"
PARAMETER_OPTION_RESPONSE_SCHEMA_PATH = CONTRACTS_ROOT / "schemas" / "parameter-option-source-response.schema.json"
ONEQUERY_SCHEMA_PATH = CONTRACTS_ROOT / "schemas" / "onequery.schema.json"
API_DATASET_SCHEMA_PATH = CONTRACTS_ROOT / "schemas" / "api-dataset.schema.json"
DYNAMIC_CUSTOM_RESPONSE_SCHEMA_PATH = CONTRACTS_ROOT / "schemas" / "dynamic-custom-source-response.schema.json"
REPORT_DSL_SCHEMA_PATH = CONTRACTS_ROOT / "schemas" / "report-dsl.schema.json"


def _read_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


_TEMPLATE_SCHEMA = _read_schema(TEMPLATE_SCHEMA_PATH)
_TEMPLATE_INSTANCE_SCHEMA = _read_schema(TEMPLATE_INSTANCE_SCHEMA_PATH)
_PARAMETER_OPTION_RESPONSE_SCHEMA = _read_schema(PARAMETER_OPTION_RESPONSE_SCHEMA_PATH)
_ONEQUERY_SCHEMA = _read_schema(ONEQUERY_SCHEMA_PATH)
_API_DATASET_SCHEMA = _read_schema(API_DATASET_SCHEMA_PATH)
_DYNAMIC_CUSTOM_RESPONSE_SCHEMA = _read_schema(DYNAMIC_CUSTOM_RESPONSE_SCHEMA_PATH)
_REPORT_DSL_SCHEMA = _read_schema(REPORT_DSL_SCHEMA_PATH)

_TEMPLATE_VALIDATOR = Draft202012Validator(_TEMPLATE_SCHEMA)
_PARAMETER_OPTION_STORE = {
    TEMPLATE_SCHEMA_PATH.name: _TEMPLATE_SCHEMA,
    f"./{TEMPLATE_SCHEMA_PATH.name}": _TEMPLATE_SCHEMA,
    TEMPLATE_SCHEMA_PATH.as_uri(): _TEMPLATE_SCHEMA,
    TEMPLATE_INSTANCE_SCHEMA_PATH.name: _TEMPLATE_INSTANCE_SCHEMA,
    f"./{TEMPLATE_INSTANCE_SCHEMA_PATH.name}": _TEMPLATE_INSTANCE_SCHEMA,
    TEMPLATE_INSTANCE_SCHEMA_PATH.as_uri(): _TEMPLATE_INSTANCE_SCHEMA,
}
_PARAMETER_OPTION_RESPONSE_VALIDATOR = Draft202012Validator(
    _PARAMETER_OPTION_RESPONSE_SCHEMA,
    resolver=RefResolver(
        base_uri=PARAMETER_OPTION_RESPONSE_SCHEMA_PATH.parent.as_uri() + "/",
        referrer=_PARAMETER_OPTION_RESPONSE_SCHEMA,
        store=_PARAMETER_OPTION_STORE,
    ),
)
_REPORT_DSL_VALIDATOR = Draft202012Validator(_REPORT_DSL_SCHEMA)
_REPORT_CATALOG_VALIDATOR = Draft202012Validator(
    {"$schema": _REPORT_DSL_SCHEMA.get("$schema"), "$defs": _REPORT_DSL_SCHEMA.get("$defs", {}), "$ref": "#/$defs/Catalog"}
)
_REPORT_SECTION_VALIDATOR = Draft202012Validator(
    {"$schema": _REPORT_DSL_SCHEMA.get("$schema"), "$defs": _REPORT_DSL_SCHEMA.get("$defs", {}), "$ref": "#/$defs/Section"}
)
_REPORT_SLIDE_VALIDATOR = Draft202012Validator(
    {"$schema": _REPORT_DSL_SCHEMA.get("$schema"), "$defs": _REPORT_DSL_SCHEMA.get("$defs", {}), "$ref": "#/$defs/Slide"}
)
_REPORT_COMPONENT_VALIDATOR = Draft202012Validator(
    {"$schema": _REPORT_DSL_SCHEMA.get("$schema"), "$defs": _REPORT_DSL_SCHEMA.get("$defs", {}), "$ref": "#/$defs/BIEngineComponent"}
)
_ONEQUERY_RESPONSE_VALIDATOR = Draft202012Validator(
    {"$schema": _ONEQUERY_SCHEMA.get("$schema"), "$defs": _ONEQUERY_SCHEMA.get("$defs", {}), "$ref": "#/$defs/OneQueryResponse"}
)
_API_DATASET_RESPONSE_VALIDATOR = Draft202012Validator(
    {"$schema": _API_DATASET_SCHEMA.get("$schema"), "$defs": _API_DATASET_SCHEMA.get("$defs", {}), "$ref": "#/$defs/ApiDatasetResponse"}
)
_DYNAMIC_CUSTOM_RESPONSE_VALIDATOR = Draft202012Validator(_DYNAMIC_CUSTOM_RESPONSE_SCHEMA)


def _build_template_instance_validator() -> Draft202012Validator:
    return Draft202012Validator(
        _TEMPLATE_INSTANCE_SCHEMA,
        resolver=RefResolver(
            base_uri=TEMPLATE_INSTANCE_SCHEMA_PATH.parent.as_uri() + "/",
            referrer=_TEMPLATE_INSTANCE_SCHEMA,
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
    _raise_first_error(_build_template_instance_validator(), candidate, "模板实例校验失败")
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


class ReportDslSchemaGateway:
    """集中校验完整 Report DSL 与外部 custom 片段。"""

    def validate_template_instance(self, payload: dict[str, Any]) -> dict[str, Any]:
        return validate_template_instance(payload)

    def validate_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._validate(_REPORT_DSL_VALIDATOR, payload, "报告 DSL 校验失败")

    def validate_catalog(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._validate(_REPORT_CATALOG_VALIDATOR, payload, "custom catalog DSL 校验失败")

    def validate_section(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._validate(_REPORT_SECTION_VALIDATOR, payload, "custom section DSL 校验失败")

    def validate_slide(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._validate(_REPORT_SLIDE_VALIDATOR, payload, "custom slide DSL 校验失败")

    def validate_components(self, payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for item in payload:
            self._validate(_REPORT_COMPONENT_VALIDATOR, item, "custom component DSL 校验失败")
        return copy.deepcopy(payload)

    def validate_onequery_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._validate(_ONEQUERY_RESPONSE_VALIDATOR, payload, "OneQuery 响应校验失败")

    def validate_api_dataset_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._validate(_API_DATASET_RESPONSE_VALIDATOR, payload, "API 数据集响应校验失败")

    def validate_dynamic_custom_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._validate(_DYNAMIC_CUSTOM_RESPONSE_VALIDATOR, payload, "custom dynamic 响应校验失败")

    @staticmethod
    def _validate(validator: Draft202012Validator, payload: dict[str, Any], prefix: str) -> dict[str, Any]:
        candidate = copy.deepcopy(payload or {})
        _raise_first_error(validator, candidate, prefix)
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
