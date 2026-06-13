"""Strict validation for DataCatalog logical entity details."""

from __future__ import annotations

from copy import deepcopy
import json

from jsonschema import Draft202012Validator

from src.shared.kernel.errors import ErrorCode, UpstreamError
from src.shared.kernel.paths import project_root
from ..application.ports import LogicalEntityValidator


LOGICAL_ENTITY_SCHEMA_PATH = (
    project_root() / "docs" / "implementation" / "contracts" / "schemas" / "logical-entity.schema.json"
)
_LOGICAL_ENTITY_SCHEMA = json.loads(LOGICAL_ENTITY_SCHEMA_PATH.read_text(encoding="utf-8"))
_LOGICAL_ENTITY_VALIDATOR = Draft202012Validator(_LOGICAL_ENTITY_SCHEMA)


class DataCatalogLogicalEntityValidator(LogicalEntityValidator):
    def validate(self, *, entity: dict, expected_name: str) -> dict:
        candidate = deepcopy(entity or {})
        errors = sorted(_LOGICAL_ENTITY_VALIDATOR.iter_errors(candidate), key=lambda item: list(item.absolute_path))
        if errors:
            error = errors[0]
            path = ".".join(str(part) for part in error.absolute_path)
            raise UpstreamError(
                f"DataCatalog 逻辑实体详情不符合契约: {path + ' ' if path else ''}{error.message}",
                details={"logicalEntityName": expected_name, "path": path},
                error_code=ErrorCode.DATA_ANALYSIS_METADATA_INVALID,
                category="upstream",
                retryable=False,
                source="datacatalog",
                http_status=502,
            )
        if candidate["name"] != expected_name:
            raise UpstreamError(
                "DataCatalog 逻辑实体详情名称与请求不一致。",
                details={"logicalEntityName": expected_name, "actualName": candidate["name"]},
                error_code=ErrorCode.DATA_ANALYSIS_METADATA_INVALID,
                category="upstream",
                retryable=False,
                source="datacatalog",
                http_status=502,
            )
        return candidate
