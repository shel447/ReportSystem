from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from .models import ReportTemplate, TemplateInstance, gen_id
from .outline_review_service import build_persisted_outline_snapshot


def capture_template_instance(
    db: Session,
    *,
    template: ReportTemplate,
    session_id: str,
    capture_stage: str,
    input_params_snapshot: Dict[str, Any],
    outline_snapshot: List[Dict[str, Any]],
    warnings: List[str] | None = None,
    report_instance_id: str | None = None,
    created_by: str = "system",
) -> TemplateInstance:
    record = TemplateInstance(
        template_instance_id=gen_id(),
        template_id=template.template_id,
        template_name=template.name or "",
        template_version=template.version or "1.0",
        session_id=session_id,
        capture_stage=capture_stage,
        input_params_snapshot=deepcopy(input_params_snapshot or {}),
        outline_snapshot=build_persisted_outline_snapshot(outline_snapshot or []),
        warnings=list(warnings or []),
        report_instance_id=report_instance_id,
        created_by=created_by or "system",
        created_at=_utcnow_naive(),
    )
    db.add(record)
    return record


def capture_generation_baseline(
    db: Session,
    *,
    template: ReportTemplate,
    session_id: str,
    report_instance_id: str,
    input_params_snapshot: Dict[str, Any],
    outline_snapshot: List[Dict[str, Any]],
    warnings: List[str] | None = None,
    created_by: str = "system",
) -> TemplateInstance:
    existing_records = (
        db.query(TemplateInstance)
        .filter(TemplateInstance.report_instance_id == report_instance_id)
        .all()
    )
    for record in existing_records:
        db.delete(record)
    return capture_template_instance(
        db,
        template=template,
        session_id=session_id,
        capture_stage="generation_baseline",
        input_params_snapshot=input_params_snapshot,
        outline_snapshot=outline_snapshot,
        warnings=warnings,
        report_instance_id=report_instance_id,
        created_by=created_by,
    )


def get_generation_baseline(db: Session, instance_id: str) -> TemplateInstance | None:
    return (
        db.query(TemplateInstance)
        .filter(TemplateInstance.report_instance_id == instance_id)
        .order_by(TemplateInstance.created_at.desc(), TemplateInstance.template_instance_id.desc())
        .first()
    )


def build_generation_baseline_payload(record: TemplateInstance) -> Dict[str, Any]:
    return {
        "instance_id": record.report_instance_id,
        "template_id": record.template_id,
        "template_name": record.template_name or record.template_id,
        "params_snapshot": deepcopy(record.input_params_snapshot or {}),
        "outline": deepcopy(record.outline_snapshot or []),
        "warnings": list(record.warnings or []),
        "created_at": str(record.created_at),
    }


def summarize_template_instance(record: TemplateInstance) -> Dict[str, Any]:
    outline_snapshot = record.outline_snapshot or []
    return {
        "template_instance_id": record.template_instance_id,
        "template_id": record.template_id,
        "template_name": record.template_name or record.template_id,
        "session_id": record.session_id or "",
        "capture_stage": record.capture_stage or "outline_saved",
        "report_instance_id": record.report_instance_id,
        "param_count": len(record.input_params_snapshot or {}),
        "outline_node_count": _count_outline_nodes(outline_snapshot),
        "outline_preview": _outline_preview(outline_snapshot),
        "created_at": str(record.created_at),
    }


def _outline_preview(nodes: List[Dict[str, Any]], limit: int = 3) -> List[str]:
    preview: List[str] = []
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        text = str(node.get("display_text") or "").strip()
        if text:
            preview.append(text)
            if len(preview) >= limit:
                return preview
        preview.extend(_outline_preview(node.get("children") or [], limit=limit - len(preview)))
        if len(preview) >= limit:
            return preview[:limit]
    return preview[:limit]


def _count_outline_nodes(nodes: List[Dict[str, Any]]) -> int:
    total = 0
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        total += 1
        total += _count_outline_nodes(node.get("children") or [])
    return total


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
