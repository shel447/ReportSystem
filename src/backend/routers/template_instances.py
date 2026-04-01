"""模板实例只读列表路由"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..infrastructure.persistence.database import get_db
from ..infrastructure.persistence.models import TemplateInstance
from ..contexts.report_runtime.infrastructure.baselines import summarize_template_instance

router = APIRouter(prefix="/template-instances", tags=["template-instances"])


@router.get("")
def list_template_instances(db: Session = Depends(get_db)):
    records = (
        db.query(TemplateInstance)
        .order_by(TemplateInstance.created_at.desc())
        .all()
    )
    return [summarize_template_instance(record) for record in records]
