from fastapi import Header


def resolve_user_id(x_user_id: object | None) -> str:
    if isinstance(x_user_id, str):
        value = x_user_id.strip()
        return value or "default"
    return "default"


def get_current_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> str:
    return resolve_user_id(x_user_id)
