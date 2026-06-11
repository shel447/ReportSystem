"""Local development implementation of the platform ``runtime.db`` SDK."""

from sqlalchemy.orm import DeclarativeBase


class TableBase(DeclarativeBase):
    """Shared declarative base for Runtime-managed ORM tables."""
