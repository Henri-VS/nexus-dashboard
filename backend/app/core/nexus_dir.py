from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

NEXUS_DIR = Path(settings.nexus_data_dir) / ".nexus"

_SUBDIRS = ("calendar", "automations", "snippets", "themes")


def ensure_nexus_dirs() -> None:
    """Create the .nexus/ directory tree on startup. Idempotent."""
    try:
        for sub in _SUBDIRS:
            (NEXUS_DIR / sub).mkdir(parents=True, exist_ok=True)
        logger.info("Nexus dir ready: %s", NEXUS_DIR)
    except OSError as exc:
        logger.error("Could not create .nexus/ dirs: %s", exc)


def nexus_path(*parts: str) -> Path:
    """Return an absolute path inside the .nexus/ directory."""
    return NEXUS_DIR.joinpath(*parts)


def list_md_files(subdir: str) -> list[Path]:
    """Return all .md files in a .nexus/ subdirectory, sorted by name."""
    target = NEXUS_DIR / subdir
    if not target.is_dir():
        return []
    return sorted(target.glob("*.md"))
