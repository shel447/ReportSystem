"""Replaceable in-process TTL cache used by platform adapters."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
import time
from typing import Any


@dataclass(slots=True)
class _CacheEntry:
    value: Any
    expires_at: float


class MemoryTtlCache:
    def __init__(self) -> None:
        self._entries: dict[str, _CacheEntry] = {}
        self._lock = RLock()

    def get(self, key: str) -> Any | None:
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= now:
                self._entries.pop(key, None)
                return None
            return entry.value

    def set(self, key: str, value: Any, *, ttl_seconds: float) -> None:
        with self._lock:
            self._entries[key] = _CacheEntry(value=value, expires_at=time.monotonic() + max(0.0, ttl_seconds))

    def clear(self, *, prefix: str | None = None) -> None:
        with self._lock:
            if prefix is None:
                self._entries.clear()
                return
            for key in [item for item in self._entries if item.startswith(prefix)]:
                self._entries.pop(key, None)


platform_cache = MemoryTtlCache()
