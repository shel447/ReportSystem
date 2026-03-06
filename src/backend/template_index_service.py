from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from .ai_gateway import OpenAICompatGateway
from .models import ReportTemplate, TemplateSemanticIndex
from .system_settings_service import build_embedding_provider_config

AUTO_MATCH_THRESHOLD = 0.66
AUTO_MATCH_GAP = 0.08
TOP_K = 3


class TemplateIndexUnavailableError(Exception):
    pass


def build_template_semantic_text(template: ReportTemplate) -> str:
    param_lines: List[str] = []
    for item in template.content_params or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        label = str(item.get("label") or "").strip()
        desc = str(item.get("description") or "").strip()
        parts = [part for part in [name, label, desc] if part]
        if parts:
            param_lines.append(" / ".join(parts))

    outline_lines: List[str] = []
    for item in template.outline or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        desc = str(item.get("description") or "").strip()
        parts = [part for part in [title, desc] if part]
        if parts:
            outline_lines.append(" / ".join(parts))

    sections = [
        f"模板名称: {template.name}",
        f"模板描述: {template.description}",
        f"场景: {template.scenario}",
        f"报告类型: {template.report_type}",
        "内容参数: " + "；".join(param_lines),
        "报告大纲: " + "；".join(outline_lines),
    ]
    return "\n".join(line for line in sections if line.split(": ", 1)[-1].strip())


def mark_template_index_stale(db: Session, template_id: str, reason: str = "模板已更新，请重建语义索引。") -> None:
    row = db.query(TemplateSemanticIndex).filter(TemplateSemanticIndex.template_id == template_id).first()
    if row is None:
        row = TemplateSemanticIndex(template_id=template_id)
        db.add(row)
    row.status = "stale"
    row.error_message = reason
    row.updated_at = datetime.utcnow()
    db.commit()


def mark_all_template_indices_stale(db: Session, reason: str = "设置已更新，请重建模板索引。") -> None:
    template_ids = [item[0] for item in db.query(ReportTemplate.template_id).all()]
    existing = {
        row.template_id: row
        for row in db.query(TemplateSemanticIndex).all()
    }
    for template_id in template_ids:
        row = existing.get(template_id)
        if row is None:
            row = TemplateSemanticIndex(template_id=template_id)
            db.add(row)
        row.status = "stale"
        row.error_message = reason
        row.updated_at = datetime.utcnow()
    db.commit()


def delete_template_index(db: Session, template_id: str) -> None:
    row = db.query(TemplateSemanticIndex).filter(TemplateSemanticIndex.template_id == template_id).first()
    if row is not None:
        db.delete(row)
        db.commit()


def get_index_status(db: Session) -> Dict[str, Any]:
    templates = db.query(ReportTemplate).order_by(ReportTemplate.created_at.desc()).all()
    indices = {
        row.template_id: row
        for row in db.query(TemplateSemanticIndex).all()
    }
    items: List[Dict[str, Any]] = []
    counts = {"ready": 0, "stale": 0, "error": 0, "missing": 0}
    for template in templates:
        index_row = indices.get(template.template_id)
        if index_row is None:
            status = "missing"
            updated_at = None
            error_message = ""
        else:
            status = index_row.status or "stale"
            updated_at = str(index_row.updated_at) if index_row.updated_at else None
            error_message = index_row.error_message or ""
        if status not in counts:
            status = "stale"
        counts[status] += 1
        items.append({
            "template_id": template.template_id,
            "template_name": template.name,
            "scenario": template.scenario or "",
            "status": status,
            "updated_at": updated_at,
            "error_message": error_message,
        })
    return {
        "total_templates": len(templates),
        "ready_count": counts["ready"],
        "stale_count": counts["stale"],
        "error_count": counts["error"],
        "missing_count": counts["missing"],
        "items": items,
    }


def reindex_all_templates(db: Session, gateway: OpenAICompatGateway) -> Dict[str, Any]:
    config = build_embedding_provider_config(db)
    templates = db.query(ReportTemplate).order_by(ReportTemplate.created_at.desc()).all()
    existing = {
        row.template_id: row
        for row in db.query(TemplateSemanticIndex).all()
    }
    active_ids = {template.template_id for template in templates}

    for template_id, row in existing.items():
        if template_id not in active_ids:
            db.delete(row)

    for template in templates:
        row = existing.get(template.template_id)
        if row is None:
            row = TemplateSemanticIndex(template_id=template.template_id)
            db.add(row)
        text = build_template_semantic_text(template)
        row.semantic_text = text
        row.embedding_model = config.model
        try:
            row.embedding_vector = gateway.create_embedding(config, [text])[0]
            row.status = "ready"
            row.error_message = None
        except Exception as exc:
            row.embedding_vector = []
            row.status = "error"
            row.error_message = str(exc)
        row.updated_at = datetime.utcnow()
    db.commit()
    return get_index_status(db)


def match_templates(db: Session, message: str, gateway: OpenAICompatGateway) -> Dict[str, Any]:
    config = build_embedding_provider_config(db)
    rows = (
        db.query(ReportTemplate, TemplateSemanticIndex)
        .join(TemplateSemanticIndex, TemplateSemanticIndex.template_id == ReportTemplate.template_id)
        .filter(TemplateSemanticIndex.status == "ready")
        .all()
    )
    if not rows:
        raise TemplateIndexUnavailableError("模板语义索引不可用，请先在“系统设置”中执行“重建模板索引”。")

    query_vector = gateway.create_embedding(config, [message])[0]
    ranked: List[Dict[str, Any]] = []
    for template, index_row in rows:
        semantic_score = _cosine_similarity(query_vector, index_row.embedding_vector or [])
        rule_score, reasons = _rule_score(template, message)
        if semantic_score >= 0.72:
            reasons.append("语义相似度高")
        elif semantic_score >= 0.56:
            reasons.append("语义相似度中等")
        total = min(1.0, semantic_score * 0.84 + min(0.16, rule_score))
        ranked.append({
            "template_id": template.template_id,
            "template_name": template.name,
            "scenario": template.scenario or "",
            "report_type": template.report_type or "",
            "score": round(total, 4),
            "semantic_score": round(semantic_score, 4),
            "match_reasons": reasons or ["基于语义向量相似度召回"],
        })

    ranked.sort(key=lambda item: item["score"], reverse=True)
    top = ranked[0]
    second_score = ranked[1]["score"] if len(ranked) > 1 else 0.0
    return {
        "auto_match": top["score"] >= AUTO_MATCH_THRESHOLD and (top["score"] - second_score) >= AUTO_MATCH_GAP,
        "best": top,
        "candidates": ranked[:TOP_K],
    }


def _rule_score(template: ReportTemplate, message: str) -> tuple[float, List[str]]:
    lowered = message.lower()
    score = 0.0
    reasons: List[str] = []
    if template.scenario and template.scenario.lower() in lowered:
        score += 0.10
        reasons.append(f"场景命中：{template.scenario}")
    if template.name and template.name.lower() in lowered:
        score += 0.06
        reasons.append(f"模板名命中：{template.name}")
    if template.report_type and template.report_type.lower() in lowered:
        score += 0.03
        reasons.append(f"报告类型命中：{template.report_type}")
    return score, reasons


def _cosine_similarity(left: List[float], right: List[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
