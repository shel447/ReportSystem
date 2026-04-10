from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..contexts.template_catalog.application.parameter_options import ParameterOptionService
from ..infrastructure.persistence.database import get_db
from ..shared.kernel.http import get_current_user_id
from ..shared.kernel.errors import ValidationError

router = APIRouter(prefix="/parameter-options", tags=["parameter-options"])


class ParameterOptionsResolveRequest(BaseModel):
    template_id: Optional[str] = None
    param_id: str
    source: str
    query: Optional[str] = None
    selected_params: Optional[dict[str, Any]] = None
    limit: Optional[int] = None


def build_parameter_option_service(_db: Session | None = None) -> ParameterOptionService:
    return ParameterOptionService()


@router.post("/resolve")
def resolve_parameter_options(
    data: ParameterOptionsResolveRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        return build_parameter_option_service(db).resolve(
            user_id=user_id,
            template_id=data.template_id,
            param_id=data.param_id,
            source=data.source,
            query=data.query,
            selected_params=data.selected_params,
            limit=data.limit,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
