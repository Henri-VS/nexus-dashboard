from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Default config ─────────────────────────────────────────────────────────────

DEFAULT_CONFIG: dict[str, Any] = {
    "master":    True,
    "ntfyUrl":   "https://ntfy.sh",
    "ntfyTopic": "",
    "security": {
        "onCrit": True, "onHigh": True, "onWarn": False, "threshold": "HIGH",
    },
    "heartbeat": {
        "onDown": True, "onRecover": True, "digest": False, "digestTime": "08:00",
    },
    "docker": {
        "onCrash": True, "onRestartThreshold": False, "restartThreshold": 3,
    },
    "automations": {"onSuccess": False, "onFailure": True},
    "study": {
        "onWorkComplete": False, "onBreakComplete": False,
        "reminder": False, "reminderTime": "09:00",
    },
    "calendar":  {"remindersEnabled": True, "reminderTime": "15m"},
    "news":      {"digest": False, "digestTime": "07:00"},
    "system": {
        "onDiskHigh": True,  "diskThreshold": 85,
        "onCpuHigh":  False, "cpuThreshold":  85,
        "onRamHigh":  False, "ramThreshold":  85,
    },
}

# ── Event → toggle-key mapping ─────────────────────────────────────────────────

_EVT: dict[str, dict[str, str]] = {
    "heartbeat":   {"down": "onDown",    "recover": "onRecover"},
    "automations": {"success": "onSuccess", "failure": "onFailure"},
    "calendar":    {"reminder": "remindersEnabled", "create": "remindersEnabled"},
    "docker":      {"crash": "onCrash",  "restart": "onRestartThreshold"},
    "security":    {"crit": "onCrit",    "high": "onHigh", "warn": "onWarn"},
}

# ── SQLite helpers ─────────────────────────────────────────────────────────────

def _db() -> str:
    return str(settings.db_path)


def ensure_table() -> None:
    with sqlite3.connect(_db()) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notification_config (
                id          INTEGER PRIMARY KEY,
                config_json TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL
            )
        """)
        conn.commit()


def _load_config() -> dict[str, Any]:
    try:
        with sqlite3.connect(_db()) as conn:
            row = conn.execute(
                "SELECT config_json FROM notification_config WHERE id = 1"
            ).fetchone()
        if row:
            stored = json.loads(row[0])
            merged: dict[str, Any] = {**DEFAULT_CONFIG}
            for k, v in stored.items():
                if isinstance(v, dict) and isinstance(merged.get(k), dict):
                    merged[k] = {**merged[k], **v}
                else:
                    merged[k] = v
            return merged
    except Exception as exc:
        logger.debug("notification_config load: %s", exc)
    return {**DEFAULT_CONFIG}


def _save_config(cfg: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(_db()) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO notification_config (id, config_json, updated_at)"
            " VALUES (1, ?, ?)",
            (json.dumps(cfg), now),
        )
        conn.commit()

# ── Core send ──────────────────────────────────────────────────────────────────

async def send_notification(
    title:    str,
    message:  str,
    feature:  str        = "general",
    event:    str | None = None,
    priority: int        = 3,
    tags:     str        = "bell",
    force:    bool       = False,
) -> bool:
    """Send a notification via Ntfy, honouring master toggle and per-feature gates."""
    cfg = _load_config()

    if not force:
        if not cfg.get("master", True):
            logger.debug("notification suppressed: master disabled")
            return False
        if feature in _EVT and event:
            key = _EVT[feature].get(event)
            if key and not cfg.get(feature, {}).get(key, True):
                logger.debug("notification suppressed: %s.%s disabled", feature, key)
                return False

    ntfy_url   = (cfg.get("ntfyUrl")   or "").strip() or settings.ntfy_url
    ntfy_topic = (cfg.get("ntfyTopic") or "").strip() or settings.ntfy_topic
    if not ntfy_topic:
        logger.debug("notification suppressed: no topic configured")
        return False

    url = f"{ntfy_url.rstrip('/')}/{ntfy_topic}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url, content=message,
                headers={"Title": title, "Priority": str(priority), "Tags": tags},
                timeout=6.0,
            )
        ok = resp.status_code < 300
        logger.debug("ntfy → %s  HTTP %d", url, resp.status_code)
        return ok
    except Exception as exc:
        logger.debug("send_notification network error: %s", exc)
        return False

# ── Pydantic ───────────────────────────────────────────────────────────────────

class SendRequest(BaseModel):
    title:    str
    message:  str
    feature:  str        = "general"
    event:    str | None = None
    priority: int        = 3
    tags:     str        = "bell"
    force:    bool       = False

# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/config")
def get_config():
    return _load_config()


@router.post("/config")
def save_config_endpoint(cfg: dict):
    _save_config(cfg)
    return {"ok": True}


@router.post("/send")
async def http_send(body: SendRequest):
    sent = await send_notification(
        body.title, body.message,
        feature=body.feature, event=body.event,
        priority=body.priority, tags=body.tags,
        force=body.force,
    )
    return {"sent": sent}


@router.post("/test")
async def test_send():
    sent = await send_notification(
        "Nexus Dashboard", "Test from Nexus Dashboard",
        feature="test", force=True,
    )
    return {"sent": sent}
