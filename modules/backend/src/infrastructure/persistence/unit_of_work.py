"""Infrastructure-owned SQLAlchemy transaction scopes."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Callable

from sqlalchemy.orm import Session

from .database import SessionLocal
from .dev_database import DevSessionLocal


class SqlAlchemyUnitOfWork(AbstractContextManager["SqlAlchemyUnitOfWork"]):
    def __init__(self, session_factory: Callable[[], Session] = SessionLocal) -> None:
        self._session_factory = session_factory
        self.session: Session | None = None

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self.session = self._session_factory()
        return self

    def commit(self) -> None:
        self._required_session().commit()

    def rollback(self) -> None:
        self._required_session().rollback()

    def __exit__(self, exc_type, exc, traceback) -> None:
        try:
            if exc_type is not None:
                self.rollback()
        finally:
            self._required_session().close()
            self.session = None

    def _required_session(self) -> Session:
        if self.session is None:
            raise RuntimeError("unit of work is not active")
        return self.session


class DevSqlAlchemyUnitOfWork(SqlAlchemyUnitOfWork):
    def __init__(self, session_factory: Callable[[], Session] = DevSessionLocal) -> None:
        super().__init__(session_factory=session_factory)
