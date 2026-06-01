from fastapi import Header, HTTPException


def resolve_user_id(x_user_id: object | None) -> str:
    if isinstance(x_user_id, str):
        value = x_user_id.strip()
        if value:
            return value
    raise HTTPException(status_code=401, detail="X-User-Id header is required")


def get_current_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> str:
    return resolve_user_id(x_user_id)
