"""Execution-local context used by approved generated-Ibis helper functions."""

from __future__ import annotations

import contextvars
from typing import Any

from .data_structure import ForeignKey


current_fk_whitelist: contextvars.ContextVar[tuple[ForeignKey, ...]] = contextvars.ContextVar(
    "current_fk_whitelist", default=()
)
current_table_config: contextvars.ContextVar[Any | None] = contextvars.ContextVar(
    "current_table_config", default=None
)
