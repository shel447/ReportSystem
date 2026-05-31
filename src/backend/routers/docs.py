from __future__ import annotations

import io
from pathlib import Path
from typing import Any
import zipfile

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse


router = APIRouter(tags=["Docs"])

DOCS_DIR = Path(__file__).resolve().parents[3] / "docs"
SUPPORTED_SUFFIXES = {".md": "markdown", ".json": "json"}


@router.get("/docs")
async def list_docs() -> list[dict[str, str]]:
    """递归列出 Markdown、Schema 和示例 JSON。"""
    _ensure_docs_dir()
    return [
        {
            "name": _relative_doc_path(path),
            "title": path.stem.replace("_", " ").replace("-", " "),
            "type": SUPPORTED_SUFFIXES[path.suffix],
        }
        for path in _iter_doc_assets()
    ]


@router.get("/docs/download.zip")
async def download_docs() -> StreamingResponse:
    """打包下载全部文档资产。"""
    _ensure_docs_dir()
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for path in _iter_doc_assets():
            zip_file.write(path, _relative_doc_path(path))

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": 'attachment; filename="docs.zip"'},
    )


@router.get("/docs/{filename:path}")
async def get_doc(filename: str) -> dict[str, Any]:
    """读取一个嵌套 Markdown 或 JSON 文档资产。"""
    _ensure_docs_dir()
    path = _resolve_doc_path(filename)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Document {filename} not found")

    return {
        "name": _relative_doc_path(path),
        "type": SUPPORTED_SUFFIXES[path.suffix],
        "content": path.read_text(encoding="utf-8"),
    }


def _ensure_docs_dir() -> None:
    if not DOCS_DIR.is_dir():
        raise HTTPException(status_code=404, detail="Docs directory not found")


def _iter_doc_assets() -> list[Path]:
    return sorted(
        path
        for path in DOCS_DIR.rglob("*")
        if path.is_file() and path.suffix in SUPPORTED_SUFFIXES
    )


def _relative_doc_path(path: Path) -> str:
    return path.resolve().relative_to(DOCS_DIR.resolve()).as_posix()


def _resolve_doc_path(filename: str) -> Path:
    requested = Path(filename)
    if requested.suffix == "":
        requested = requested.with_suffix(".md")
    if requested.suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(status_code=404, detail=f"Document {filename} not found")

    candidate = (DOCS_DIR / requested).resolve()
    if not candidate.is_relative_to(DOCS_DIR.resolve()):
        raise HTTPException(status_code=404, detail=f"Document {filename} not found")
    return candidate
