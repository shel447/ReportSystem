"""外部 custom dynamic 内容服务适配器。"""

from __future__ import annotations

from typing import Any

from .external_business import ExternalBusinessGateway


class CustomContentGateway:
    """通过 HTTP POST 获取 custom dynamic 目录或章节 DSL 片段。"""

    def __init__(self, *, gateway: ExternalBusinessGateway | None = None) -> None:
        self.gateway = gateway or ExternalBusinessGateway()

    def post_json(self, *, url: str, payload: dict[str, Any], user_id: str = "default") -> dict[str, Any]:
        return self.gateway.post_json(path_or_url=url, payload=payload, user_id=user_id)
