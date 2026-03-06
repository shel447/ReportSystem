from __future__ import annotations

import json
import math
import re
import unicodedata
from datetime import datetime
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from sqlalchemy.orm import Session

from .ai_gateway import OpenAICompatGateway
from .models import ReportTemplate, TemplateSemanticIndex
from .system_settings_service import build_embedding_provider_config

AUTO_MATCH_THRESHOLD = 0.68
AUTO_MATCH_GAP = 0.06
TOP_K = 3
QUERY_NOISE_PHRASES = (
    "请帮我",
    "帮我",
    "我想",
    "想要",
    "我要",
    "麻烦",
    "请",
    "一下",
    "一个",
    "一份",
    "做个",
    "做一份",
    "写个",
    "写一份",
    "生成",
    "统计一下",
)
REPORT_SUFFIXES = ("报告", "模板", "日报", "周报", "月报", "年报", "简报", "报表")


class TemplateIndexUnavailableError(Exception):
    pass


def build_template_semantic_text(template: ReportTemplate) -> str:
    param_lines: List[str] = []
    for item in _as_list(template.content_params):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        label = str(item.get("label") or "").strip()
        desc = str(item.get("description") or "").strip()
        parts = [part for part in [label, name, desc] if part]
        if parts:
            param_lines.append(" / ".join(parts))

    outline_lines: List[str] = []
    for item in _as_list(template.outline):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        desc = str(item.get("description") or "").strip()
        parts = [part for part in [title, desc] if part]
        if parts:
            outline_lines.append(" / ".join(parts))

    keyword_text = "；".join(_string_list(template.match_keywords))
    sections = [
        f"模板名称: {template.name}",
        f"模板描述: {template.description}",
        f"场景: {template.scenario}",
        f"报告类型: {template.report_type}",
        f"匹配关键词: {keyword_text}",
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
    query_norm = _normalize_text(message)
    ranked: List[Dict[str, Any]] = []
    for template, index_row in rows:
        semantic_score = _cosine_similarity(query_vector, index_row.embedding_vector or [])
        rule = _rule_score(template, query_norm)
        semantic_weight = 0.50 if rule["strong_direct"] else 0.74
        total = min(1.0, semantic_score * semantic_weight + min(0.56, rule["score"]))
        reasons = _finalize_reasons(rule["reasons"], semantic_score)
        ranked.append({
            "template_id": template.template_id,
            "template_name": template.name or "未命名模板",
            "scenario": template.scenario or "",
            "description": template.description or "",
            "report_type": template.report_type or "",
            "score": round(total, 4),
            "score_label": _score_label(total),
            "semantic_score": round(semantic_score, 4),
            "rule_score": round(rule["score"], 4),
            "match_reasons": reasons,
        })

    ranked.sort(key=lambda item: (item["score"], item["rule_score"], item["semantic_score"]), reverse=True)
    top = ranked[0]
    second_score = ranked[1]["score"] if len(ranked) > 1 else 0.0
    return {
        "auto_match": top["score"] >= AUTO_MATCH_THRESHOLD and (top["score"] - second_score) >= AUTO_MATCH_GAP,
        "best": top,
        "candidates": ranked[:TOP_K],
    }


def _rule_score(template: ReportTemplate, query_norm: str) -> Dict[str, Any]:
    score = 0.0
    strong_direct = False
    reasons: List[Tuple[int, str]] = []

    name = str(template.name or "").strip()
    name_match = _match_phrase(query_norm, name, allow_core_terms=True)
    if name_match == "full":
        score += 0.34
        strong_direct = True
        reasons.append((100, f"模板名命中：{name}"))
    elif name_match == "core":
        score += 0.30
        strong_direct = True
        reasons.append((96, f"模板名命中：{name}"))
    elif name_match == "partial":
        score += 0.20
        reasons.append((88, f"模板名接近：{name}"))

    keyword_match = _best_phrase_match(query_norm, _string_list(template.match_keywords), allow_core_terms=True)
    if keyword_match:
        if keyword_match[0] == "full":
            score += 0.30
            strong_direct = True
            reasons.append((98, f"关键词命中：{keyword_match[1]}"))
        elif keyword_match[0] == "core":
            score += 0.24
            strong_direct = True
            reasons.append((92, f"关键词命中：{keyword_match[1]}"))
        else:
            score += 0.16
            reasons.append((82, f"关键词接近：{keyword_match[1]}"))

    desc_match = _best_phrase_match(query_norm, [template.description] if template.description else [])
    if desc_match:
        score += 0.09 if desc_match[0] in {"full", "core"} else 0.06
        reasons.append((70, f"描述命中：{desc_match[1]}"))

    scenario_match = _best_phrase_match(query_norm, [template.scenario] if template.scenario else [], allow_core_terms=True)
    if scenario_match:
        score += 0.08 if scenario_match[0] in {"full", "core"} else 0.05
        reasons.append((74, f"场景命中：{scenario_match[1]}"))

    param_match = _best_phrase_match(query_norm, _param_phrases(template))
    if param_match:
        score += 0.07 if param_match[0] in {"full", "core"} else 0.05
        reasons.append((66, f"参数命中：{param_match[1]}"))

    outline_match = _best_phrase_match(query_norm, _outline_phrases(template), allow_core_terms=True)
    if outline_match:
        score += 0.07 if outline_match[0] in {"full", "core"} else 0.05
        reasons.append((62, f"大纲命中：{outline_match[1]}"))

    report_type_match = _best_phrase_match(query_norm, [template.report_type] if template.report_type else [])
    if report_type_match:
        score += 0.03
        reasons.append((50, f"报告类型命中：{report_type_match[1]}"))

    return {
        "score": min(0.56, score),
        "strong_direct": strong_direct,
        "reasons": reasons,
    }


def _best_phrase_match(query_norm: str, phrases: Sequence[str], *, allow_core_terms: bool = False):
    best = None
    rank = {"full": 3, "core": 2, "partial": 1}
    for phrase in phrases:
        mode = _match_phrase(query_norm, phrase, allow_core_terms=allow_core_terms)
        if not mode:
            continue
        candidate = (mode, str(phrase).strip())
        if best is None or rank[mode] > rank[best[0]]:
            best = candidate
    return best


def _match_phrase(query_norm: str, phrase: str, *, allow_core_terms: bool = False) -> str | None:
    phrase_norm = _normalize_text(phrase)
    if len(phrase_norm) < 2 or len(query_norm) < 2:
        return None
    if phrase_norm in query_norm:
        return "full"

    core = _trim_report_suffixes(phrase_norm)
    if allow_core_terms and _core_terms_present(query_norm, core):
        return "core"

    if _fuzzy_phrase_overlap(query_norm, core):
        return "partial"
    return None


def _finalize_reasons(reason_pairs: Sequence[Tuple[int, str]], semantic_score: float) -> List[str]:
    ordered: List[str] = []
    seen = set()
    for _, text in sorted(reason_pairs, key=lambda item: item[0], reverse=True):
        if text in seen:
            continue
        seen.add(text)
        ordered.append(text)
        if len(ordered) >= 2:
            break

    semantic_reason = None
    if semantic_score >= 0.78:
        semantic_reason = "语义相似度高"
    elif semantic_score >= 0.62:
        semantic_reason = "语义相似度中等"
    elif not ordered and semantic_score >= 0.45:
        semantic_reason = "语义相似度接近"

    if semantic_reason:
        ordered.append(semantic_reason)
    if not ordered:
        ordered.append("基于语义向量召回")
    return ordered[:3]


def _score_label(score: float) -> str:
    if score >= 0.78:
        return "高相关"
    if score >= 0.58:
        return "中相关"
    return "低相关"


def _param_phrases(template: ReportTemplate) -> List[str]:
    phrases: List[str] = []
    for item in _as_list(template.content_params):
        if not isinstance(item, dict):
            continue
        for key in ("label", "name", "description"):
            value = str(item.get(key) or "").strip()
            if value:
                phrases.append(value)
    return phrases


def _outline_phrases(template: ReportTemplate) -> List[str]:
    phrases: List[str] = []
    for item in _as_list(template.outline):
        if not isinstance(item, dict):
            continue
        for key in ("title", "description"):
            value = str(item.get(key) or "").strip()
            if value:
                phrases.append(value)
    return phrases


def _core_terms_present(query_norm: str, phrase_norm: str) -> bool:
    if not phrase_norm:
        return False
    core = _trim_report_suffixes(phrase_norm)
    if core and core in query_norm:
        return True
    terms = _split_core_terms(core)
    return bool(terms) and all(term in query_norm for term in terms)


def _split_core_terms(text: str) -> List[str]:
    if not text:
        return []
    parts = [part for part in re.split(r"[^0-9a-z\u4e00-\u9fff]+", text) if part]
    terms: List[str] = []
    for part in parts or [text]:
        if re.fullmatch(r"[\u4e00-\u9fff]+", part):
            if len(part) == 2:
                terms.append(part)
                continue
            if len(part) <= 8 and len(part) % 2 == 0:
                terms.extend(part[i:i + 2] for i in range(0, len(part), 2))
                continue
            terms.append(part)
            continue
        if re.fullmatch(r"[0-9a-z]+", part):
            if len(part) >= 2:
                terms.append(part)
            continue
        if len(part) <= 4:
            terms.append(part)
            continue
        if len(part) <= 8 and len(part) % 2 == 0:
            terms.extend(part[i:i + 2] for i in range(0, len(part), 2))
            continue
        terms.append(part)
    return [term for term in dict.fromkeys(term for term in terms if len(term) >= 2)]


def _fuzzy_phrase_overlap(query_norm: str, phrase_norm: str) -> bool:
    if not phrase_norm:
        return False
    char_overlap = len(set(query_norm) & set(phrase_norm)) / max(1, len(set(phrase_norm)))
    if len(phrase_norm) <= 6 and char_overlap >= 0.75:
        return True
    bigram_overlap = _ngram_overlap(query_norm, phrase_norm, 2)
    return bigram_overlap >= 0.42


def _ngram_overlap(left: str, right: str, size: int) -> float:
    if len(left) < size or len(right) < size:
        return 0.0
    left_grams = {left[i:i + size] for i in range(len(left) - size + 1)}
    right_grams = {right[i:i + size] for i in range(len(right) - size + 1)}
    if not right_grams:
        return 0.0
    return len(left_grams & right_grams) / len(right_grams)


def _normalize_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", str(text or "")).lower()
    for phrase in QUERY_NOISE_PHRASES:
        value = value.replace(phrase, "")
    value = re.sub(r"[\s\u3000]+", "", value)
    value = re.sub(r"[^0-9a-z\u4e00-\u9fff]", "", value)
    return value


def _trim_report_suffixes(text: str) -> str:
    current = text
    changed = True
    while changed:
        changed = False
        for suffix in REPORT_SUFFIXES:
            if current.endswith(suffix) and len(current) > len(suffix) + 1:
                current = current[: -len(suffix)]
                changed = True
    return current


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except ValueError:
            return []
        return loaded if isinstance(loaded, list) else []
    return []


def _string_list(values: Any) -> List[str]:
    items: List[str] = []
    for value in _as_list(values):
        text = str(value or "").strip()
        if text:
            items.append(text)
    return list(dict.fromkeys(items))


def _cosine_similarity(left: List[float], right: List[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
