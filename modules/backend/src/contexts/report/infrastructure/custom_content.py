"""外部 custom dynamic 内容服务适配器。"""

from __future__ import annotations

from typing import Any

import httpx


class CustomContentGateway:
    """通过 HTTP POST 获取 custom dynamic 目录或章节 DSL 片段。"""

    def __init__(self, *, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds

    def post_json(self, *, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise ValueError("custom dynamic response must be a JSON object")
        return data
