from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError as PydanticValidationError

from ..shared.kernel.errors import ApplicationError, ErrorCode, ValidationError
from ..shared.kernel.http import resolve_user_id

T = TypeVar("T", bound=BaseModel)


def parse_body(body: Any, model: type[T]) -> T:
    try:
        return model.model_validate(body)
    except PydanticValidationError as exc:
        raise ApplicationError(
            "输入参数校验失败，请检查请求内容。",
            details={"errors": exc.errors()},
            error_code=ErrorCode.BASE_PARAM_INVALID,
            category="param",
            http_status=400,
        ) from exc


def user_id(req) -> str:
    return resolve_user_id(getattr(req, "current_user_id", None))


def required_query(req, query: dict[str, Any], name: str) -> str:
    raw_values = list(getattr(req.request, "query_arguments", {}).get(name, []))
    if len(raw_values) != 1:
        raise ValidationError(
            f"查询参数 {name} 必须且只能提供一次。",
            details={"parameter": name},
        )
    value = str(query.get(name) or "").strip()
    if not value:
        raise ValidationError(
            f"查询参数 {name} 不能为空。",
            details={"parameter": name},
        )
    return value


def write_json(req, payload: Any, *, status: int = 200) -> None:
    req.set_status(status)
    req.set_header("Content-Type", "application/json; charset=UTF-8")
    req.finish(json.dumps(payload, ensure_ascii=False))
