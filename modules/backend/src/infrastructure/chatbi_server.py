"""ReportSystem lifecycle and application-lifetime infrastructure."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, TypeVar

from .configuration import initialize_config_center
from .dependencies import conversation_service_scope, report_service_scope
from .demo.telecom import init_telecom_demo_db
from .persistence.dev_database import init_dev_db
from .platform.runtime import audit_publisher, build_policy_auth_gateway, start_platform_runtime, stop_platform_runtime
from ..shared.kernel.log import start_log_level_monitor, stop_log_level_monitor

T = TypeVar("T")


class ChatBIServer:
    def __init__(self) -> None:
        self.executor: ThreadPoolExecutor | None = None
        self.policy_auth_gateway = None
        self.audit_publisher = audit_publisher
        self.report_service_scope = report_service_scope
        self.conversation_service_scope = conversation_service_scope

    def initialize(self) -> None:
        if self.executor is not None:
            return
        init_dev_db()
        init_telecom_demo_db()
        start_log_level_monitor()
        initialize_config_center()
        start_platform_runtime()
        self.executor = ThreadPoolExecutor(max_workers=16, thread_name_prefix="report-web")
        self.policy_auth_gateway = build_policy_auth_gateway()

    def destroy(self) -> None:
        stop_platform_runtime()
        stop_log_level_monitor()
        if self.executor is not None:
            self.executor.shutdown(wait=False, cancel_futures=True)
            self.executor = None

    async def run_blocking(self, call: Callable[..., T], *args, **kwargs) -> T:
        if self.executor is None:
            raise RuntimeError("ChatBIServer is not initialized")
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, lambda: call(*args, **kwargs))
