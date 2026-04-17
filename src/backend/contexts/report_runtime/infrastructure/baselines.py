from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ....infrastructure.persistence.models import ReportTemplate, TemplateInstance, gen_id
from .outline import build_persisted_outline_snapshot


def capture_template_instance(
    db: Session,
    *,
    template: ReportTemplate,
    session_id: str,
    capture_stage: str,
    input_params_snapshot: Dict[str, Any],
    outline_snapshot: List[Dict[str, Any]],
    generated_sections: List[Dict[str, Any]] | None = None,
    warnings: List[str] | None = None,
    report_instance_id: str | None = None,
    created_by: str = "system",
) -> TemplateInstance:
    existing = _find_existing_template_instance(
        db,
        template_id=template.template_id,
        session_id=session_id,
        report_instance_id=report_instance_id,
    )
    outline_nodes = build_persisted_outline_snapshot(outline_snapshot or [])
    if existing:
        current = deepcopy(existing.content or {})
        revision = max(1, int(((current.get("instance_meta") or {}).get("revision")) or 1) + 1)
        existing.capture_stage = capture_stage
        existing.template_name = template.name or ""
        existing.template_version = template.version or "1.0"
        if report_instance_id:
            existing.report_instance_id = report_instance_id
        existing.session_id = session_id or existing.session_id
        existing.content = _build_template_instance_content(
            template=template,
            session_id=existing.session_id or session_id,
            input_params_snapshot=input_params_snapshot,
            outline_snapshot=outline_nodes,
            generated_sections=generated_sections,
            warnings=warnings,
            report_instance_id=existing.report_instance_id,
            capture_stage=capture_stage,
            status=_capture_stage_to_status(capture_stage),
            revision=revision,
            existing_content=current,
        )
        return existing

    record = TemplateInstance(
        template_instance_id=gen_id(),
        template_id=template.template_id,
        template_name=template.name or "",
        template_version=template.version or "1.0",
        session_id=session_id,
        capture_stage=capture_stage,
        report_instance_id=report_instance_id,
        created_by=created_by or "system",
        created_at=_utcnow_naive(),
        content=_build_template_instance_content(
            template=template,
            session_id=session_id,
            input_params_snapshot=input_params_snapshot,
            outline_snapshot=outline_nodes,
            generated_sections=generated_sections,
            warnings=warnings,
            report_instance_id=report_instance_id,
            capture_stage=capture_stage,
            status=_capture_stage_to_status(capture_stage),
            revision=1,
            existing_content=None,
        ),
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
    generated_sections: List[Dict[str, Any]] | None = None,
    warnings: List[str] | None = None,
    created_by: str = "system",
) -> TemplateInstance:
    return capture_template_instance(
        db,
        template=template,
        session_id=session_id,
        capture_stage="generation_baseline",
        input_params_snapshot=input_params_snapshot,
        outline_snapshot=outline_snapshot,
        generated_sections=generated_sections,
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
    content = deepcopy(record.content or {})
    baseline_payload = {
        "schema_version": str(content.get("schema_version") or getattr(record, "schema_version", "") or "ti.v1.0"),
        "status": str((content.get("instance_meta") or {}).get("status") or getattr(record, "status", "") or ""),
        "revision": max(1, int(((content.get("instance_meta") or {}).get("revision")) or getattr(record, "revision", 1) or 1)),
        "created_at": str(((content.get("instance_meta") or {}).get("created_at")) or record.created_at),
        "template_snapshot": deepcopy(content.get("base_template") or {}),
        "runtime_state": deepcopy(content.get("runtime_state") or {}),
        "resolved_view": deepcopy(content.get("resolved_view") or {}),
        "generated_content": deepcopy(content.get("generated_content") or {}),
        "fragments": deepcopy(content.get("fragments") or {}),
    }
    return {
        "instance_id": record.report_instance_id,
        "template_id": record.template_id,
        "template_name": record.template_name or record.template_id,
        "params_snapshot": deepcopy(record.input_params_snapshot or {}),
        "outline": deepcopy(record.outline_snapshot or []),
        "warnings": list(record.warnings or []),
        "created_at": str(record.created_at),
        "generation_baseline": baseline_payload,
    }


def summarize_template_instance(record: TemplateInstance) -> Dict[str, Any]:
    outline_snapshot = record.outline_snapshot or []
    content = deepcopy(getattr(record, "content", {}) or {})
    instance_meta = content.get("instance_meta") if isinstance(content.get("instance_meta"), dict) else {}
    return {
        "template_instance_id": record.template_instance_id,
        "template_id": record.template_id,
        "template_name": record.template_name or record.template_id,
        "session_id": record.session_id or "",
        "capture_stage": record.capture_stage or "outline_saved",
        "status": str(instance_meta.get("status") or _capture_stage_to_status(record.capture_stage)),
        "revision": max(1, int(instance_meta.get("revision") or 1)),
        "schema_version": str(content.get("schema_version") or getattr(record, "schema_version", "") or "ti.v1.0"),
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


def _capture_stage_to_status(capture_stage: str) -> str:
    normalized = str(capture_stage or "").strip()
    if normalized == "generation_baseline":
        return "completed"
    if normalized == "outline_confirmed":
        return "ready_for_confirmation"
    return "collecting_parameters"


def _find_existing_template_instance(
    db: Session,
    *,
    template_id: str,
    session_id: str,
    report_instance_id: str | None,
) -> TemplateInstance | None:
    if report_instance_id:
        existing = (
            db.query(TemplateInstance)
            .filter(TemplateInstance.report_instance_id == report_instance_id)
            .order_by(TemplateInstance.created_at.desc(), TemplateInstance.template_instance_id.desc())
            .first()
        )
        if existing:
            return existing
    return (
        db.query(TemplateInstance)
        .filter(
            TemplateInstance.template_id == template_id,
            TemplateInstance.session_id == session_id,
            TemplateInstance.report_instance_id.is_(None),
        )
        .order_by(TemplateInstance.created_at.desc(), TemplateInstance.template_instance_id.desc())
        .first()
    )


def _build_template_instance_content(
    *,
    template: ReportTemplate,
    session_id: str,
    input_params_snapshot: Dict[str, Any],
    outline_snapshot: List[Dict[str, Any]],
    generated_sections: List[Dict[str, Any]] | None,
    warnings: List[str] | None,
    report_instance_id: str | None,
    capture_stage: str,
    status: str,
    revision: int,
    existing_content: Dict[str, Any] | None,
) -> Dict[str, Any]:
    now_text = datetime.now(UTC).isoformat()
    old = deepcopy(existing_content or {})
    old_generated = old.get("generated_content") if isinstance(old.get("generated_content"), dict) else {}
    old_fragments = old.get("fragments") if isinstance(old.get("fragments"), dict) else {}
    parameters = deepcopy(input_params_snapshot or {})
    effective_generated_sections = deepcopy(
        generated_sections if generated_sections is not None else old_generated.get("sections", [])
    )
    return {
        "schema_version": "ti.v1.0",
        "base_template": {
            "id": template.template_id,
            "category": template.category or "",
            "name": template.name or "",
            "description": template.description or "",
            "parameters": deepcopy(template.parameters or []),
            "sections": deepcopy(template.sections or []),
        },
        "instance_meta": {
            "status": status,
            "revision": max(1, int(revision or 1)),
            "created_at": str((old.get("instance_meta") or {}).get("created_at") or now_text),
            "updated_at": now_text,
            "last_updated_by": "system",
            "conversation_id": session_id or "",
            "chat_id": "",
        },
        "runtime_state": {
            "parameter_runtime": {
                "definitions": deepcopy(template.parameters or []),
                "candidate_snapshots": deepcopy((old.get("runtime_state") or {}).get("parameter_runtime", {}).get("candidate_snapshots", [])),
                "selections": [
                    {"param_id": key, "value": _to_resolved_trio(value)}
                    for key, value in (parameters or {}).items()
                ],
                "confirmation": {
                    "missing_param_ids": [],
                    "confirmed": status in {"ready_for_confirmation", "confirmed", "generating", "completed"},
                },
            },
            "outline_runtime": {
                "current_outline_instance": deepcopy(outline_snapshot),
            },
        },
        "resolved_view": {
            "parameters": {key: _to_resolved_trio(value) for key, value in (parameters or {}).items()},
            "outline": deepcopy(outline_snapshot),
            "sections": deepcopy(effective_generated_sections),
        },
        "generated_content": {
            "sections": deepcopy(effective_generated_sections),
            "documents": deepcopy(old_generated.get("documents", [])),
        },
        "fragments": deepcopy(old_fragments),
        # Legacy compatibility fields kept for old serializers and tests.
        "input_params_snapshot": deepcopy(parameters),
        "outline_snapshot": deepcopy(outline_snapshot),
        "warnings": list(warnings or []),
        "session_id": session_id or "",
        "report_instance_id": report_instance_id,
    }


def _to_resolved_trio(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict) and {"display", "value", "query"}.issubset(value.keys()):
        return {
            "display": deepcopy(value.get("display")),
            "value": deepcopy(value.get("value")),
            "query": deepcopy(value.get("query")),
        }
    return {
        "display": deepcopy(value),
        "value": deepcopy(value),
        "query": deepcopy(value),
    }
