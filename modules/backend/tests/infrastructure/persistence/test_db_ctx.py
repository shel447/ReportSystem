from __future__ import annotations

import pytest

from src.infrastructure.persistence import db_ctx


class Session:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.closes = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closes += 1


class Instance:
    def __init__(self, *sessions):
        self.sessions = list(sessions)
        self.calls = 0

    def session(self):
        self.calls += 1
        return self.sessions.pop(0)


def test_db_session_commits_and_closes(monkeypatch):
    session = Session()
    monkeypatch.setattr(db_ctx, "_instance", Instance(session))

    with db_ctx.db_session(reraise=True) as active:
        assert active is session

    assert (session.commits, session.rollbacks, session.closes) == (1, 0, 1)


def test_db_session_rolls_back_and_swallows_by_default(monkeypatch):
    session = Session()
    monkeypatch.setattr(db_ctx, "_instance", Instance(session))

    with db_ctx.db_session():
        raise RuntimeError("boom")

    assert (session.commits, session.rollbacks, session.closes) == (0, 1, 1)


def test_db_session_reraises_original_error(monkeypatch):
    session = Session()
    monkeypatch.setattr(db_ctx, "_instance", Instance(session))

    with pytest.raises(RuntimeError, match="boom"):
        with db_ctx.db_session(reraise=True):
            raise RuntimeError("boom")

    assert (session.commits, session.rollbacks, session.closes) == (0, 1, 1)


def test_db_session_logs_failures(monkeypatch):
    session = Session()
    calls = []
    monkeypatch.setattr(db_ctx, "_instance", Instance(session))
    monkeypatch.setattr(db_ctx.logger, "exception", lambda message, *args: calls.append((message, args)))

    with db_ctx.db_session():
        raise ValueError("invalid")

    assert len(calls) == 1
    assert calls[0][0] == "db error: %s"
    assert isinstance(calls[0][1][0], ValueError)
    assert str(calls[0][1][0]) == "invalid"


def test_db_session_requests_a_fresh_runtime_session_per_scope(monkeypatch):
    first = Session()
    second = Session()
    instance = Instance(first, second)
    monkeypatch.setattr(db_ctx, "_instance", instance)

    with db_ctx.db_session():
        pass
    with db_ctx.db_session():
        pass

    assert instance.calls == 2
    assert first.closes == second.closes == 1
