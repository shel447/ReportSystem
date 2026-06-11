"""ReportSystem logging facade built on the platform runtime logger."""

from __future__ import annotations

import os
import re
import threading
from pathlib import Path
from typing import Callable

from runtime.config import Ini
from runtime.log import get_log, set_level

LOG_METHODS = ("debug", "info", "warn", "error", "critical", "exception")
SENSITIVE_REPLACEMENT = "******"
_SENSITIVE_KEYS = (
    "kafka.ssl.key.password",
    "ssl.key.password",
    "password",
    "passwd",
    "pwd",
    "bspsession",
    "roarand",
    "secret",
    "sessionId",
    "cookie",
    "encrypt",
    "dencrypt",
    "decrypt",
    "auth",
    "token",
    "apikey",
    "api_key",
)
SENSITIVE_PATTERN = re.compile(
    rf"(?P<key>{'|'.join(re.escape(item) for item in _SENSITIVE_KEYS)})"
    r"(?P<separator>\s*[:=]\s*)"
    r"(?P<quote>[\"']?)"
    r"(?P<value>[^\"'\s,}]+)",
    re.IGNORECASE,
)
_CONTROL_CHARACTER_ESCAPES = (
    ("\n", r"\n"),
    ("\r", r"\r"),
    ("\t", r"\t"),
    ("\v", r"\v"),
    ("\f", r"\f"),
    ("\b", r"\b"),
)


def _escape_for_log(value: object) -> object:
    if not isinstance(value, str):
        return value
    escaped = value
    for original, replacement in _CONTROL_CHARACTER_ESCAPES:
        escaped = escaped.replace(original, replacement)
    return escaped


def _mask_sensitive(value: object) -> object:
    if not isinstance(value, str):
        return value

    def replace(match: re.Match[str]) -> str:
        secret = match.group("value")
        prefix = secret[:1]
        return (
            f"{match.group('key')}{match.group('separator')}"
            f"{match.group('quote')}{prefix}{SENSITIVE_REPLACEMENT}"
        )

    return SENSITIVE_PATTERN.sub(replace, value)


def _sanitize(value: object) -> object:
    return _escape_for_log(_mask_sensitive(value))


def _patch_log_method(method):
    def patched(message: object, *args: object, **kwargs):
        sanitized_kwargs = {key: _sanitize(value) for key, value in kwargs.items()}
        return method(
            _sanitize(message),
            *(_sanitize(arg) for arg in args),
            **sanitized_kwargs,
        )

    return patched


def _configure_logger(runtime_logger):
    runtime_logger.depth = 3
    if getattr(runtime_logger, "_chatbi_kernel_patched", False):
        return runtime_logger
    for method_name in LOG_METHODS:
        setattr(runtime_logger, method_name, _patch_log_method(getattr(runtime_logger, method_name)))
    runtime_logger._chatbi_kernel_patched = True
    return runtime_logger


logger = _configure_logger(get_log("chatbi"))
algo_logger = _configure_logger(get_log("ir_flow"))


class LogLevelMonitor:
    """Monitor the runtime INI log level for the ChatBI process lifetime."""

    def __init__(
        self,
        *,
        config_file_path: str | None = None,
        interval_seconds: float = 30,
        level_setter: Callable[[str | int], None] = set_level,
    ) -> None:
        self.config_file_path = config_file_path
        self.interval_seconds = interval_seconds
        self.level_setter = level_setter
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_mtime: float | None = None
        self._last_log_level: str | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        path = self.config_file_path or os.environ.get("PY_RUNTIME_FILE")
        if not path:
            logger.warn("PY_RUNTIME_FILE environment variable not set, log level monitoring disabled")
            return
        self.config_file_path = path
        self._stop_event.clear()
        self._refresh()
        self._thread = threading.Thread(
            target=self._run,
            name="chatbi-log-level-monitor",
            daemon=True,
        )
        self._thread.start()
        logger.info("Log level monitor started for file: %s", path)

    def stop(self) -> None:
        thread = self._thread
        if thread is None:
            return
        self._stop_event.set()
        thread.join(timeout=max(1.0, min(self.interval_seconds + 0.5, 5.0)))
        self._thread = None

    def _run(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            self._refresh()

    def _refresh(self) -> None:
        path = Path(str(self.config_file_path or ""))
        try:
            if not path.exists():
                logger.warn("Config file not found: %s, will retry", path)
                return
            current_mtime = path.stat().st_mtime
            if current_mtime == self._last_mtime:
                return
            self._last_mtime = current_mtime
            runtime_config = Ini()
            runtime_config.load(path)
            new_log_level = str(runtime_config.get("log", "level") or "").strip()
            if not new_log_level or new_log_level == self._last_log_level:
                return
            self.level_setter(new_log_level)
            self._last_log_level = new_log_level
            logger.info("Log level changed to: %s", new_log_level)
        except Exception as exc:
            logger.exception("Error monitoring log level: %s", exc)


log_level_monitor = LogLevelMonitor()


def start_log_level_monitor() -> None:
    log_level_monitor.start()


def stop_log_level_monitor() -> None:
    log_level_monitor.stop()
