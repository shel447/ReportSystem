import pytest

from src.shared.kernel.errors import ValidationError
from src.shared.kernel.http import resolve_user_id


def test_resolve_user_id_requires_header_by_default(monkeypatch):
    monkeypatch.delenv("REPORT_DEV_USER_ID", raising=False)

    with pytest.raises(ValidationError):
        resolve_user_id(None)


def test_resolve_user_id_uses_explicit_development_user(monkeypatch):
    monkeypatch.setenv("REPORT_DEV_USER_ID", " pycharm-check ")

    assert resolve_user_id(None) == "pycharm-check"
    assert resolve_user_id(" actual-user ") == "actual-user"
