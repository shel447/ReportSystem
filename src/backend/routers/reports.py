"""Aggregated report view routes."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..infrastructure.dependencies import build_report_runtime_service
from ..infrastructure.persistence.database import get_db
from ..shared.kernel.errors import NotFoundError
from ..shared.kernel.http import resolve_user_id

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{report_id}")
def get_report_view(
    report_id: str,
    db: Session = Depends(get_db),
    user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
):
    try:
        return build_report_runtime_service(db).get_report_view(report_id, user_id=resolve_user_id(user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
