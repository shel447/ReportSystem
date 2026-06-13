"""Strict validation for DataCatalog logical relationship details."""

from __future__ import annotations

from copy import deepcopy
import json

from jsonschema import Draft202012Validator

from src.shared.kernel.errors import ErrorCode, UpstreamError
from src.shared.kernel.paths import project_root
from ..application.ports import LogicalRelationshipValidator


SCHEMA_PATH = project_root() / "docs" / "implementation" / "contracts" / "schemas" / "logical-relationship.schema.json"
_VALIDATOR = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


class DataCatalogLogicalRelationshipValidator(LogicalRelationshipValidator):
    def validate(self, *, relationship: dict, expected_name: str) -> dict:
        candidate = deepcopy(relationship or {})
        errors = sorted(_VALIDATOR.iter_errors(candidate), key=lambda item: list(item.absolute_path))
        if errors:
            error = errors[0]
            path = ".".join(str(part) for part in error.absolute_path)
            raise UpstreamError(
                f"DataCatalog 逻辑关系详情不符合契约: {path + ' ' if path else ''}{error.message}",
                details={"logicalRelationshipName": expected_name, "path": path},
                error_code=ErrorCode.DATA_ANALYSIS_METADATA_INVALID,
                category="upstream",
                retryable=False,
                source="datacatalog",
                http_status=502,
            )
        if candidate["name"] != expected_name:
            raise UpstreamError(
                "DataCatalog 逻辑关系详情名称与请求不一致。",
                details={"logicalRelationshipName": expected_name, "actualName": candidate["name"]},
                error_code=ErrorCode.DATA_ANALYSIS_METADATA_INVALID,
                category="upstream",
                retryable=False,
                source="datacatalog",
                http_status=502,
            )
        return candidate
