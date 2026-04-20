"""基于 dataclass field metadata 的公开字段别名工具。"""

from __future__ import annotations

from dataclasses import Field, fields
from functools import lru_cache
from typing import Any


@lru_cache(maxsize=None)
def _field_map(model_type: type) -> dict[str, Field[Any]]:
    return {item.name: item for item in fields(model_type)}


def get_alias(model_type: type, field_name: str) -> str:
    """返回字段对外公开时使用的名称。"""

    field_def = _field_map(model_type)[field_name]
    return str(field_def.metadata.get("alias") or field_def.name)


def get_value(payload: dict[str, Any], model_type: type, field_name: str, default: Any = None) -> Any:
    """按字段别名从公开载荷中读取值。"""

    return payload.get(get_alias(model_type, field_name), default)


def set_value(payload: dict[str, Any], model_type: type, field_name: str, value: Any) -> None:
    """按字段别名向公开载荷写值。"""

    payload[get_alias(model_type, field_name)] = value

