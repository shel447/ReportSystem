"""Runtime-managed database session scope for formal business data."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from runtime.cache import zenith_instance
from sqlalchemy.orm import Session

from ...shared.kernel.log import logger

_instance = zenith_instance("dtesmartbiservicedb")


@contextmanager
def db_session(reraise: bool = False) -> Generator[Session, None, None]:
    """Commit a Runtime Session or roll it back when the scope fails."""

    session: Session = _instance.session()
    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.exception("db error: %s", exc)
        if reraise:
            raise
    finally:
        session.close()
