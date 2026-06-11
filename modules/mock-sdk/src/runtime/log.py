"""Local development implementation of the platform ``runtime.log`` SDK."""

from __future__ import annotations

import logging
import threading
from typing import Any

_LOCK = threading.RLock()
_LOGGERS: dict[str, "RuntimeLogger"] = {}
_LEVEL = logging.INFO


class RuntimeLogger:
    """Small runtime logger surface intentionally excluding ``warning``."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.depth = 0
        self._logger = logging.getLogger(name)
        self._logger.setLevel(_LEVEL)

    def debug(self, message: object, *args: object, **kwargs: Any) -> None:
        self._logger.debug(message, *args, **kwargs)

    def info(self, message: object, *args: object, **kwargs: Any) -> None:
        self._logger.info(message, *args, **kwargs)

    def warn(self, message: object, *args: object, **kwargs: Any) -> None:
        self._logger.warning(message, *args, **kwargs)

    def error(self, message: object, *args: object, **kwargs: Any) -> None:
        self._logger.error(message, *args, **kwargs)

    def critical(self, message: object, *args: object, **kwargs: Any) -> None:
        self._logger.critical(message, *args, **kwargs)

    def exception(self, message: object, *args: object, **kwargs: Any) -> None:
        self._logger.exception(message, *args, **kwargs)


def get_log(name: str) -> RuntimeLogger:
    """Return the stable runtime logger for ``name``."""

    normalized = str(name or "").strip()
    if not normalized:
        raise ValueError("logger name is required")
    with _LOCK:
        logger = _LOGGERS.get(normalized)
        if logger is None:
            logger = RuntimeLogger(normalized)
            _LOGGERS[normalized] = logger
        return logger


def set_level(level: str | int) -> None:
    """Set the level of existing and future runtime loggers."""

    global _LEVEL
    normalized = _normalize_level(level)
    with _LOCK:
        _LEVEL = normalized
        for logger in _LOGGERS.values():
            logger._logger.setLevel(normalized)


def _normalize_level(level: str | int) -> int:
    if isinstance(level, bool):
        raise ValueError("invalid log level")
    if isinstance(level, int):
        return level
    name = str(level or "").strip().upper()
    value = logging.getLevelNamesMapping().get(name)
    if value is None:
        raise ValueError(f"invalid log level: {level}")
    return value
