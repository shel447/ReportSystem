from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..contexts.report.application.template_models import parameter_options_result_to_dict
from ..contexts.report.domain.template_models import parameter_value_from_dict
from ..infrastructure.dependencies import build_report_service
from ..infrastructure.persistence.database import get_db
from ..shared.kernel.http import get_current_user_id
from ..shared.kernel.errors import ValidationError

router = APIRouter(prefix="/parameter-options", tags=["parameter-options"])


class ParameterOptionsResolveRequest(BaseModel):
    parameterId: str
    source: str
    contextValues: dict[str, list[dict[str, Any]]]


@router.post("/resolve")
def resolve_parameter_options(
    data: ParameterOptionsResolveRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        return parameter_options_result_to_dict(
            build_report_service(db).resolve_parameter_options(
                user_id=user_id,
                parameter_id=data.parameterId,
                source=data.source,
                context_values={
                    parameter_id: [parameter_value_from_dict(item) for item in values]
                    for parameter_id, values in data.contextValues.items()
                },
            )
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
