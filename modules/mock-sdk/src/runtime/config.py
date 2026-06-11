"""Local development implementation of ``runtime.config.Ini``."""

from __future__ import annotations

from configparser import ConfigParser
import os
from pathlib import Path
from typing import Iterable


class Ini:
    def __init__(self, path: str | os.PathLike[str] | None = None) -> None:
        configured = path or os.getenv("RUNTIME_CONFIG_FILE")
        self.path = Path(configured).expanduser() if configured else None
        self._parser = ConfigParser()
        if self.path is not None and self.path.exists():
            self._parser.read(self.path, encoding="utf-8")

    def sections(self) -> list[str]:
        return self._parser.sections()

    def items(self, section: str) -> Iterable[tuple[str, str]]:
        return self._parser.items(section) if self._parser.has_section(section) else ()

    def get(self, section: str, option: str, fallback=None):
        return self._parser.get(section, option, fallback=fallback)

    def getint(self, section: str, option: str, fallback=None):
        return self._parser.getint(section, option, fallback=fallback)

    def getfloat(self, section: str, option: str, fallback=None):
        return self._parser.getfloat(section, option, fallback=fallback)

    def getboolean(self, section: str, option: str, fallback=None):
        return self._parser.getboolean(section, option, fallback=fallback)
