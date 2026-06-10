from __future__ import annotations

import io
from pathlib import Path
import zipfile

from ..shared.kernel.errors import NotFoundError
from ..shared.kernel.paths import project_root
from ..web.base import DevHandler

DOCS_DIR = project_root() / "docs"
SUPPORTED_SUFFIXES = {".md": "markdown", ".json": "json"}


class DocsHandler(DevHandler):
    async def get(self):
        _ensure_docs_dir()
        self.write_json([{"name": _relative(path), "title": path.stem.replace("_", " ").replace("-", " "), "type": SUPPORTED_SUFFIXES[path.suffix]} for path in _assets()])


class DocsDownloadHandler(DevHandler):
    async def get(self):
        _ensure_docs_dir()
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in _assets():
                archive.write(path, _relative(path))
        self.set_header("Content-Type", "application/x-zip-compressed")
        self.set_header("Content-Disposition", 'attachment; filename="docs.zip"')
        self.finish(output.getvalue())


class DocHandler(DevHandler):
    async def get(self, filename: str):
        _ensure_docs_dir()
        path = _resolve(filename)
        if not path.is_file():
            raise NotFoundError(f"Document {filename} not found")
        self.write_json({"name": _relative(path), "type": SUPPORTED_SUFFIXES[path.suffix], "content": path.read_text(encoding="utf-8")})


def _ensure_docs_dir() -> None:
    if not DOCS_DIR.is_dir():
        raise NotFoundError("Docs directory not found")


def _assets() -> list[Path]:
    return sorted(path for path in DOCS_DIR.rglob("*") if path.is_file() and path.suffix in SUPPORTED_SUFFIXES)


def _relative(path: Path) -> str:
    return path.resolve().relative_to(DOCS_DIR.resolve()).as_posix()


def _resolve(filename: str) -> Path:
    requested = Path(filename)
    if requested.suffix == "":
        requested = requested.with_suffix(".md")
    if requested.suffix not in SUPPORTED_SUFFIXES:
        raise NotFoundError(f"Document {filename} not found")
    candidate = (DOCS_DIR / requested).resolve()
    if not candidate.is_relative_to(DOCS_DIR.resolve()):
        raise NotFoundError(f"Document {filename} not found")
    return candidate


ROUTES = [
    (r"/rest/dev/docs", DocsHandler),
    (r"/rest/dev/docs/download\.zip", DocsDownloadHandler),
    (r"/rest/dev/docs/(.+)", DocHandler),
]
