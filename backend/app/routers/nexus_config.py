from __future__ import annotations

import logging
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.core.nexus_dir import nexus_path

logger = logging.getLogger(__name__)
router = APIRouter()

# Only allow safe filenames: alphanumeric, hyphens, underscores, dots.
_SAFE_NAME = re.compile(r"^[\w\-]+\.(css|md)$")


def _safe_filename(filename: str, extension: str) -> str:
    """Raise 400 if filename is not a safe single-component name."""
    if not _SAFE_NAME.match(filename) or not filename.endswith(f".{extension}"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return filename


# ── Snippets ──────────────────────────────────────────────────────────────────

@router.get("/snippets")
def list_snippets() -> list[str]:
    """Return filenames of all CSS snippets in .nexus/snippets/."""
    snippets_dir = nexus_path("snippets")
    if not snippets_dir.is_dir():
        return []
    return sorted(p.name for p in snippets_dir.glob("*.css"))


@router.get("/snippets/{filename}", response_class=PlainTextResponse)
def get_snippet(filename: str) -> str:
    """Return the CSS content of a single snippet file."""
    _safe_filename(filename, "css")
    path = nexus_path("snippets", filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Snippet not found")
    return path.read_text(encoding="utf-8")


class SnippetBody(BaseModel):
    content: str


@router.post("/snippets/{filename}", status_code=200)
def write_snippet(filename: str, body: SnippetBody) -> dict:
    """Write (create or overwrite) a CSS snippet file."""
    _safe_filename(filename, "css")
    path = nexus_path("snippets", filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.content, encoding="utf-8")
    logger.info("Snippet written: %s", path)
    return {"ok": True, "filename": filename}


# ── Themes ────────────────────────────────────────────────────────────────────

@router.get("/themes")
def list_themes() -> list[str]:
    """Return filenames of all CSS themes in .nexus/themes/."""
    themes_dir = nexus_path("themes")
    if not themes_dir.is_dir():
        return []
    return sorted(p.name for p in themes_dir.glob("*.css"))
