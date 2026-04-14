from __future__ import annotations

from typing import Any

import httpx

from ....infrastructure.demo.dynamic_sources import get_dynamic_option_items
from ....shared.kernel.errors import ValidationError

DEFAULT_LIMIT = 10
MAX_LIMIT = 50
MAX_REQUEST_BODY_BYTES = 32 * 1024
UPSTREAM_TIMEOUT_SECONDS = 3.0


class ParameterOptionService:
    def resolve(
        self,
        *,
        user_id: str,
        template_id: str | None,
        param_id: str,
        source: str,
        query: str | None = None,
        selected_params: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        resolved_limit = DEFAULT_LIMIT if limit is None else int(limit)
        if resolved_limit < 1 or resolved_limit > MAX_LIMIT:
            raise ValidationError("limit must be between 1 and 50")

        payload = {
            "template_id": template_id,
            "param_id": param_id,
            "source": source,
            "query": query or "",
            "selected_params": selected_params or {},
            "limit": resolved_limit,
        }
        body_size = len(httpx.Request("POST", "http://local", json=payload).content)
        if body_size > MAX_REQUEST_BODY_BYTES:
            raise ValidationError("request body too large")

        if source.startswith("api:/"):
            raw_items = get_dynamic_option_items(source)
            items = [_normalize_option_item(item) for item in raw_items[:resolved_limit]]
            return {
                "items": [item for item in items if item],
                "meta": {
                    "source": source,
                    "limit": resolved_limit,
                    "returned": len([item for item in items if item]),
                    "has_more": len(raw_items) > len([item for item in items if item]),
                    "truncated": len(raw_items) > len([item for item in items if item]),
                    "retryable": False,
                },
            }

        if source.startswith("http://") or source.startswith("https://"):
            upstream_payload = {
                "request_id": f"{user_id}:{param_id}",
                "source": source,
                "query": query or "",
                "context": {
                    "template_id": template_id,
                    "param_id": param_id,
                    "selected_params": selected_params or {},
                },
                "limit": resolved_limit,
            }
            try:
                with httpx.Client(timeout=UPSTREAM_TIMEOUT_SECONDS) as client:
                    response = client.post(source, json=upstream_payload)
                    response.raise_for_status()
                    data = response.json()
            except httpx.TimeoutException:
                return _empty_result(source, resolved_limit, retryable=True, error_code="PARAM_SOURCE_TIMEOUT")
            except Exception:
                return _empty_result(source, resolved_limit, retryable=True, error_code="PARAM_SOURCE_UPSTREAM_ERROR")

            raw_items = data.get("items")
            if not isinstance(raw_items, list):
                return _empty_result(source, resolved_limit, retryable=False, error_code="PARAM_SOURCE_RESPONSE_INVALID")
            items: list[dict[str, Any]] = []
            for item in raw_items[:resolved_limit]:
                normalized = _normalize_option_item(item)
                if not normalized:
                    return _empty_result(source, resolved_limit, retryable=False, error_code="PARAM_SOURCE_RESPONSE_INVALID")
                items.append(normalized)
            return {
                "items": items,
                "meta": {
                    "source": source,
                    "limit": resolved_limit,
                    "returned": len(items),
                    "has_more": bool(data.get("has_more")),
                    "truncated": len(raw_items) > len(items),
                    "retryable": False,
                },
            }

        raise ValidationError("unsupported dynamic parameter source")


def _normalize_option_item(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    label = str(item.get("label") or "").strip()
    value = item.get("value")
    query = item.get("query")
    if not label or not _is_scalar(value) or not _is_scalar_or_scalar_list(query):
        return None
    return {
        "label": label[:64],
        "value": value,
        "query": query,
    }


def _is_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool))


def _is_scalar_or_scalar_list(value: Any) -> bool:
    if _is_scalar(value):
        return True
    if isinstance(value, list):
        return all(_is_scalar(item) for item in value)
    return False


def _empty_result(source: str, limit: int, *, retryable: bool, error_code: str) -> dict[str, Any]:
    return {
        "items": [],
        "meta": {
            "source": source,
            "limit": limit,
            "returned": 0,
            "has_more": False,
            "truncated": False,
            "retryable": retryable,
            "error_code": error_code,
        },
    }
