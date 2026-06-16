import time
from pathlib import Path

import aiofiles
from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings

router = APIRouter()

_raw = settings.obsidian_vault_path
VAULT: Path | None = Path(_raw) if _raw else None

_now = time.time()
_MOCK_NOTES = [
    {"path": "Security/THM-notes.md",  "name": "THM-notes",     "modified": _now - 2 * 3_600},
    {"path": "Projects/homelab.md",    "name": "homelab",        "modified": _now - 18 * 3_600},
    {"path": "Daily/2026-06-08.md",    "name": "2026-06-08",     "modified": _now - 5 * 3_600},
    {"path": "Security/wazuh-setup.md","name": "wazuh-setup",    "modified": _now - 2 * 86_400},
    {"path": "Certs/security-plus.md", "name": "security-plus",  "modified": _now - 3 * 86_400},
]


def _vault_ok() -> bool:
    return VAULT is not None and VAULT.exists()


@router.get("/recent")
async def get_recent_notes(limit: int = 5):
    if not _vault_ok():
        return _MOCK_NOTES[:limit]

    md_files = sorted(
        VAULT.rglob("*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]

    return [
        {
            "path":     str(f.relative_to(VAULT)),
            "name":     f.stem,
            "modified": f.stat().st_mtime,
        }
        for f in md_files
    ]


@router.get("/file")
async def get_note_file(path: str = Query(...)):
    """Return the raw markdown content of a single note."""
    if not _vault_ok():
        raise HTTPException(status_code=503, detail="Vault not mounted")

    # Resolve both sides before comparison to block path-traversal
    vault_resolved  = VAULT.resolve()
    target          = (VAULT / path).resolve()
    try:
        target.relative_to(vault_resolved)
    except ValueError:
        raise HTTPException(status_code=400, detail="Path traversal denied")

    if not target.exists():
        raise HTTPException(status_code=404, detail="Note not found")

    async with aiofiles.open(target, "r", encoding="utf-8", errors="replace") as f:
        content = await f.read()

    return {"path": path, "name": target.stem, "content": content}
