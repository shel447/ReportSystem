import os

from .errors import ErrorCode, ValidationError


def resolve_user_id(x_user_id: object | None) -> str:
    if isinstance(x_user_id, str):
        value = x_user_id.strip()
        if value:
            return value
    development_user_id = str(os.getenv("REPORT_DEV_USER_ID") or "").strip()
    if development_user_id:
        return development_user_id
    raise ValidationError(
        "请先登录后再使用报告系统。",
        error_code=ErrorCode.BASE_AUTH_REQUIRED,
        category="auth",
        http_status=401,
    )
