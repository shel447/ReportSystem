"""Application-lifetime infrastructure composition."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from ..infrastructure.dependencies import conversation_service_scope, report_service_scope
from ..infrastructure.platform.runtime import build_policy_auth_gateway


class WebContainer:
    def __init__(self) -> None:
        self.executor = ThreadPoolExecutor(max_workers=16, thread_name_prefix="report-web")
        self.policy_auth_gateway = build_policy_auth_gateway()
        self.report_service_scope = report_service_scope
        self.conversation_service_scope = conversation_service_scope

    def close(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)
