from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ....infrastructure.persistence.models import ReportDocument, ReportInstance, ReportTemplate, gen_id

DOCUMENTS_DIR = os.path.join(os.path.dirname(__file__), "generated_documents")
SUPPORTED_DOCUMENT_FORMATS = {"md": "md", "markdown": "md"}


class DocumentGenerationError(Exception):
    pass


def ensure_documents_dir() -> None:
    os.makedirs(DOCUMENTS_DIR, exist_ok=True)


def create_markdown_document(db: Session, instance_id: str) -> ReportDocument:
    ensure_documents_dir()
    instance = db.query(ReportInstance).filter(ReportInstance.instance_id == instance_id).first()
    if not instance:
        raise DocumentGenerationError("Instance not found")

    template = db.query(ReportTemplate).filter(ReportTemplate.template_id == instance.template_id).first()
    version = _next_version(db, instance_id, "md")
    markdown = _build_markdown(instance, template)
    filename = _build_filename(template.name if template else "报告文档", instance.instance_id, version)
    absolute_path = os.path.join(DOCUMENTS_DIR, filename)

    with open(absolute_path, "w", encoding="utf-8") as handle:
        handle.write(markdown)

    relative_path = os.path.relpath(absolute_path, os.path.dirname(__file__))
    file_size = os.path.getsize(absolute_path)
    document = ReportDocument(
        document_id=gen_id(),
        instance_id=instance.instance_id,
        template_id=instance.template_id,
        format="md",
        file_path=relative_path.replace("\\", "/"),
        file_size=file_size,
        version=version,
        status="ready",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def resolve_document_absolute_path(file_path: str) -> str:
    if not file_path:
        raise DocumentGenerationError("Document file path is empty")
    if os.path.isabs(file_path):
        return file_path
    absolute = os.path.normpath(os.path.join(os.path.dirname(__file__), file_path))
    return absolute


def remove_document_file(document: ReportDocument) -> None:
    try:
        absolute = resolve_document_absolute_path(document.file_path)
    except DocumentGenerationError:
        return
    if os.path.exists(absolute):
        os.remove(absolute)


def normalize_document_format(format_name: str) -> str:
    normalized = SUPPORTED_DOCUMENT_FORMATS.get(str(format_name or "").strip().lower())
    if not normalized:
        raise DocumentGenerationError("当前仅支持生成 Markdown 文档。")
    return normalized


def serialize_document(document: ReportDocument) -> Dict[str, Any]:
    return {
        "document_id": document.document_id,
        "instance_id": document.instance_id,
        "template_id": document.template_id,
        "format": document.format,
        "file_path": document.file_path,
        "file_name": os.path.basename(document.file_path or ""),
        "file_size": document.file_size,
        "status": document.status,
        "version": document.version,
        "download_url": f"/api/documents/{document.document_id}/download",
        "created_at": str(document.created_at),
    }


def _next_version(db: Session, instance_id: str, fmt: str) -> int:
    latest = (
        db.query(ReportDocument)
        .filter(ReportDocument.instance_id == instance_id, ReportDocument.format == fmt)
        .order_by(ReportDocument.version.desc())
        .first()
    )
    if not latest:
        return 1
    return int(latest.version or 1) + 1


def _build_filename(template_name: str, instance_id: str, version: int) -> str:
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "-", str(template_name or "report")).strip("-")
    slug = slug[:48] if slug else "report"
    return f"{slug}-{instance_id[:8]}-v{version}.md"


def _build_markdown(instance: ReportInstance, template: ReportTemplate | None) -> str:
    title = template.name if template else "报告文档"
    outline = list(instance.outline_content or [])
    lines: List[str] = [
        f"# {title}",
        "",
        f"- 实例 ID: `{instance.instance_id}`",
        f"- 模板 ID: `{instance.template_id}`",
        f"- 模板版本: `{instance.template_version}`",
        f"- 状态: `{instance.status}`",
        f"- 导出时间: `{datetime.now().isoformat(timespec='seconds')}`",
        "",
        "## 输入参数",
        "",
        "```json",
        json.dumps(instance.input_params or {}, ensure_ascii=False, indent=2, default=str),
        "```",
        "",
    ]

    if not outline:
        lines.extend(["## 正文", "", "当前实例没有可导出的章节内容。"])
        return "\n".join(lines).strip() + "\n"

    for index, section in enumerate(outline, start=1):
        lines.extend(_render_section(section, index))

    return "\n".join(lines).strip() + "\n"


def _render_section(section: Dict[str, Any], index: int) -> List[str]:
    title = str(section.get("title") or f"章节 {index}").strip()
    content = str(section.get("content") or "").strip()
    status = str(section.get("status") or "unknown").strip()
    data_status = str(section.get("data_status") or "unknown").strip()
    lines = [
        f"## {index}. {title}",
        "",
        f"- 生成状态: `{status}`",
        f"- 数据状态: `{data_status}`",
    ]
    description = str(section.get("description") or "").strip()
    if description:
        lines.append(f"- 章节描述: {description}")
    lines.append("")

    normalized_content = _strip_duplicate_heading(content, title)
    if normalized_content:
        lines.append(normalized_content)
    else:
        lines.append("该章节暂无正文。")
    lines.append("")
    return lines


def _strip_duplicate_heading(content: str, title: str) -> str:
    if not content:
        return ""
    lines = content.splitlines()
    if not lines:
        return content
    first = lines[0].strip()
    if first.startswith("#"):
        heading = first.lstrip("#").strip()
        if heading == title:
            return "\n".join(lines[1:]).strip()
    return content
