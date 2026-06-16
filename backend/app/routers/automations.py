from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sqlite3
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from app.core.config import settings
from app.core.frontmatter import parse_frontmatter
from app.core.nexus_dir import list_md_files, nexus_path
from app.routers.notifications import send_notification

logger = logging.getLogger(__name__)
router = APIRouter()

# ── SQLModel schemas ──────────────────────────────────────────────────────────
# Automation table kept for backward compat; no longer written to after migration.

class Automation(SQLModel, table=True):
    __tablename__ = "automations"
    id:             Optional[int] = Field(default=None, primary_key=True)
    name:           str           = Field(index=True)
    description:    str           = Field(default="")
    enabled:        bool          = Field(default=True)
    trigger_type:   str           = Field(index=True)
    trigger_config: str           = Field(default="{}")
    action_type:    str           = Field(index=True)
    action_config:  str           = Field(default="{}")
    last_run:       Optional[str] = Field(default=None)
    run_count:      int           = Field(default=0)
    created_at:     str           = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class AutomationLog(SQLModel, table=True):
    __tablename__ = "automation_logs"
    id:            Optional[int] = Field(default=None, primary_key=True)
    automation_id: str           = Field(index=True)   # string ID from .md frontmatter
    ran_at:        str
    success:       bool
    result:        str           = Field(default="")

# ── SQLite log helpers (SQLite is correct for append-only run logs) ───────────

def _db() -> str:
    return settings.db_path

def _log_run(aid: str, success: bool, result: str) -> None:
    ran_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(_db()) as conn:
        conn.execute(
            "INSERT INTO automation_logs (automation_id, ran_at, success, result) VALUES (?,?,?,?)",
            (aid, ran_at, success, result),
        )
        # Keep only the last 50 runs per automation.
        conn.execute("""
            DELETE FROM automation_logs WHERE id IN (
                SELECT id FROM automation_logs
                WHERE automation_id = ?
                ORDER BY id DESC LIMIT -1 OFFSET 50
            )
        """, (aid,))
        conn.commit()
    # Persist last_run and incremented run_count back to the .md file.
    row = _get(aid)
    if row is not None:
        _update(aid, {"last_run": ran_at, "run_count": row["run_count"] + 1})

def _get_logs(aid: str, limit: int = 20) -> list[dict]:
    with sqlite3.connect(_db()) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM automation_logs WHERE automation_id = ? ORDER BY id DESC LIMIT ?",
            (aid, limit),
        ).fetchall()
    return [dict(r) for r in rows]

# ── File-based CRUD ───────────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "automation"

def _new_id() -> str:
    return uuid.uuid4().hex[:8]

def _fm_to_row(meta: dict, body: str) -> dict:
    """Convert parsed frontmatter + body into the internal row dict."""
    trigger = meta.get("trigger") or {}
    action  = meta.get("action")  or {}
    return {
        "id":             str(meta.get("id", "")),
        "name":           meta.get("name", ""),
        "description":    body.strip(),
        "enabled":        bool(meta.get("enabled", True)),
        "trigger_type":   trigger.get("type", ""),
        "trigger_config": {k: v for k, v in trigger.items() if k != "type"},
        "action_type":    action.get("type", ""),
        "action_config":  {k: v for k, v in action.items() if k != "type"},
        "last_run":       meta.get("last_run"),    # None or ISO string
        "run_count":      int(meta.get("run_count", 0)),
        "created_at":     str(meta.get("created_at", "")),
    }

def _row_to_yaml(row: dict) -> str:
    """Serialise internal row dict back to YAML frontmatter text (no delimiters)."""
    trigger_dict: dict = {"type": row.get("trigger_type", ""), **( row.get("trigger_config") or {})}
    action_dict:  dict = {"type": row.get("action_type",  ""), **( row.get("action_config")  or {})}
    fm = {
        "id":         row["id"],
        "name":       row["name"],
        "enabled":    row.get("enabled", True),
        "trigger":    trigger_dict,
        "action":     action_dict,
        "last_run":   row.get("last_run"),
        "run_count":  row.get("run_count", 0),
        "created_at": row.get("created_at", ""),
    }
    return yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)

def _write_file(path: Path, row: dict) -> None:
    yaml_text = _row_to_yaml(row)
    body = (row.get("description") or "").strip()
    text = f"---\n{yaml_text}---\n"
    if body:
        text += f"\n{body}\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def _read_file(path: Path) -> dict | None:
    try:
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        if not meta.get("id"):
            return None
        return _fm_to_row(meta, body)
    except Exception as exc:
        logger.warning("Could not read automation file %s: %s", path, exc)
        return None

def _all() -> list[dict]:
    return [r for p in list_md_files("automations") if (r := _read_file(p)) is not None]

def _find_path(aid: str) -> Path | None:
    for p in list_md_files("automations"):
        try:
            meta, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
            if str(meta.get("id", "")) == aid:
                return p
        except Exception:
            continue
    return None

def _get(aid: str) -> dict | None:
    path = _find_path(aid)
    return _read_file(path) if path else None

def _insert(row: dict) -> dict:
    slug = _slugify(row["name"])
    path = nexus_path("automations", f"{slug}_{row['id'][:8]}.md")
    _write_file(path, row)
    return row

def _update(aid: str, changes: dict) -> dict | None:
    path = _find_path(aid)
    if not path:
        return None
    row = _read_file(path)
    if row is None:
        return None
    row.update(changes)
    new_path = nexus_path("automations", f"{_slugify(row['name'])}_{aid[:8]}.md")
    _write_file(new_path, row)
    if path != new_path:
        path.unlink(missing_ok=True)
    return row

def _delete(aid: str) -> bool:
    path = _find_path(aid)
    if not path:
        return False
    path.unlink(missing_ok=True)
    return True

# ── Startup migration: SQLite → .nexus/automations/ ──────────────────────────

def migrate_automations_from_sqlite() -> None:
    """
    One-time migration. Reads automations from the old SQLite table and writes
    each one as a .md file in .nexus/automations/. Skipped if any .md files
    already exist (migration already happened or user created files manually).
    """
    if list_md_files("automations"):
        return  # already migrated

    try:
        with sqlite3.connect(_db()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM automations ORDER BY id").fetchall()
    except Exception as exc:
        logger.warning("Migration: could not read SQLite automations: %s", exc)
        return

    if not rows:
        return

    for sqlite_row in rows:
        r = dict(sqlite_row)
        try:
            tc = json.loads(r.get("trigger_config") or "{}")
            ac = json.loads(r.get("action_config")  or "{}")
        except Exception:
            tc, ac = {}, {}

        row: dict = {
            "id":             _new_id(),
            "name":           r.get("name", "unnamed"),
            "description":    r.get("description", ""),
            "enabled":        bool(r.get("enabled", True)),
            "trigger_type":   r.get("trigger_type", ""),
            "trigger_config": tc,
            "action_type":    r.get("action_type", ""),
            "action_config":  ac,
            "last_run":       r.get("last_run"),
            "run_count":      int(r.get("run_count", 0)),
            "created_at":     r.get("created_at") or datetime.now(timezone.utc).isoformat(),
        }
        _insert(row)
        logger.info("Migrated automation %r → %s", r["name"], row["id"])

    logger.info("Migrated %d automation(s) from SQLite to .nexus/automations/", len(rows))

# ── Action executors ──────────────────────────────────────────────────────────

async def _run_action(action_type: str, action_config: dict) -> tuple[bool, str]:
    try:
        if action_type == "ntfy_notify":
            return await _action_ntfy(action_config)
        if action_type == "docker_restart":
            return await _action_docker_restart(action_config)
        if action_type == "webhook":
            return await _action_webhook(action_config)
        if action_type == "log_entry":
            return _action_log_entry(action_config)
        if action_type == "bash_script":
            return _action_bash(action_config)
        return False, f"Unknown action type: {action_type}"
    except Exception as exc:
        return False, f"Error: {exc}"

async def _action_ntfy(cfg: dict) -> tuple[bool, str]:
    title = cfg.get("title", "Dashboard Automation")
    msg   = cfg.get("message", "")
    pri   = int(cfg.get("priority", 3))
    sent  = await send_notification(
        title=title, message=msg,
        feature="automations", tags="automation", priority=pri,
    )
    return sent, "ntfy: sent" if sent else "ntfy: blocked by notification settings or not configured"

async def _action_docker_restart(cfg: dict) -> tuple[bool, str]:
    name = cfg.get("container", "")
    if not name:
        return False, "container name not specified"
    try:
        import docker  # type: ignore
        cli = docker.from_env()
        c   = cli.containers.get(name)
        c.restart()
        return True, f"Restarted container: {name}"
    except Exception as exc:
        return False, f"docker restart error: {exc}"

async def _action_webhook(cfg: dict) -> tuple[bool, str]:
    url     = cfg.get("url", "")
    method  = cfg.get("method", "POST").upper()
    headers = cfg.get("headers", {})
    body    = cfg.get("body", "")
    if not url:
        return False, "webhook URL not specified"
    if isinstance(headers, str):
        try:
            headers = json.loads(headers)
        except Exception:
            headers = {}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.request(method, url, headers=headers, content=body, timeout=10.0)
        return r.status_code < 300, f"webhook: HTTP {r.status_code}"
    except Exception as exc:
        return False, f"webhook error: {exc}"

def _action_log_entry(cfg: dict) -> tuple[bool, str]:
    level   = cfg.get("level", "INFO").upper()
    message = cfg.get("message", "Automation triggered")
    from app.routers.logs import _insert_raw
    ts = datetime.now(timezone.utc).isoformat()
    _insert_raw(ts, level, "automation", message)
    return True, f"Log entry written: [{level}] {message}"

def _action_bash(cfg: dict) -> tuple[bool, str]:
    if not os.getenv("ALLOW_BASH_AUTOMATION", "").lower() in ("1", "true", "yes"):
        return False, "ALLOW_BASH_AUTOMATION not enabled"
    cmd = cfg.get("command", "")
    if not cmd:
        return False, "No command specified"
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30,
        )
        out = (result.stdout + result.stderr).strip()[:500]
        return result.returncode == 0, f"exit {result.returncode}: {out}"
    except subprocess.TimeoutExpired:
        return False, "Command timed out (30s)"
    except Exception as exc:
        return False, f"bash error: {exc}"

# ── Trigger evaluation ────────────────────────────────────────────────────────

_SEV_RANK = {"INFO": 0, "WARN": 1, "WARNING": 1, "HIGH": 2, "CRIT": 3, "CRITICAL": 3}

def _check_trigger(ttype: str, tconfig: dict, context: dict) -> bool:
    if ttype == "wazuh_alert":
        min_sev = tconfig.get("min_severity", "CRIT")
        evt_sev = context.get("severity", "INFO")
        return _SEV_RANK.get(evt_sev, 0) >= _SEV_RANK.get(min_sev, 3)

    if ttype == "service_down":
        svc = tconfig.get("service", "")
        return context.get("service") == svc and context.get("status") == "down"

    if ttype == "service_up":
        svc = tconfig.get("service", "")
        return context.get("service") == svc and context.get("status") == "up"

    if ttype == "docker_restart":
        name      = tconfig.get("container", "")
        threshold = int(tconfig.get("threshold", 3))
        return (
            context.get("container") == name
            and int(context.get("restarts", 0)) >= threshold
        )

    return False

async def evaluate_event_triggers(event_type: str, context: dict) -> None:
    """Called by other routers when a triggerable event occurs."""
    for a in _all():
        if not a["enabled"] or a["trigger_type"] != event_type:
            continue
        tconfig = a.get("trigger_config") or {}
        if not _check_trigger(event_type, tconfig, context):
            continue
        aconfig = a.get("action_config") or {}
        ok, msg = await _run_action(a["action_type"], aconfig)
        _log_run(a["id"], ok, msg)
        logger.info("Automation %s (%s) triggered by %s: %s", a["id"], a["name"], event_type, msg)

# ── Schedule loop ─────────────────────────────────────────────────────────────

_INTERVAL_SECONDS = {
    "15m":   15 * 60,
    "1h":    60 * 60,
    "6h":    6  * 60 * 60,
    "daily": 24 * 60 * 60,
}

_last_schedule_run: dict[str, float] = {}

async def schedule_loop() -> None:
    import time
    logger.info("Automation schedule loop started")
    while True:
        await asyncio.sleep(60)
        now = time.monotonic()
        try:
            automations = _all()
        except Exception as exc:
            logger.error("schedule_loop fetch: %s", exc)
            continue

        for a in automations:
            if not a["enabled"] or a["trigger_type"] != "schedule":
                continue
            try:
                tconfig    = a.get("trigger_config") or {}
                interval   = tconfig.get("interval", "1h")
                interval_s = _INTERVAL_SECONDS.get(interval, 3600)
                last       = _last_schedule_run.get(a["id"], 0)
                if now - last < interval_s:
                    continue
                _last_schedule_run[a["id"]] = now
                aconfig = a.get("action_config") or {}
                ok, msg = await _run_action(a["action_type"], aconfig)
                _log_run(a["id"], ok, msg)
                logger.info("Schedule automation %s (%s): %s", a["id"], a["name"], msg)
            except Exception as exc:
                logger.error("schedule automation %s: %s", a["id"], exc)

# ── Request / response models ─────────────────────────────────────────────────

class AutomationCreate(BaseModel):
    name:           str
    description:    str            = ""
    enabled:        bool           = True
    trigger_type:   str
    trigger_config: dict[str, Any] = {}
    action_type:    str
    action_config:  dict[str, Any] = {}

class AutomationUpdate(BaseModel):
    name:           Optional[str]            = None
    description:    Optional[str]            = None
    enabled:        Optional[bool]           = None
    trigger_type:   Optional[str]            = None
    trigger_config: Optional[dict[str, Any]] = None
    action_type:    Optional[str]            = None
    action_config:  Optional[dict[str, Any]] = None

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
def list_automations():
    return _all()

@router.post("", status_code=201)
def create_automation(body: AutomationCreate):
    row: dict = {
        "id":             _new_id(),
        "name":           body.name,
        "description":    body.description,
        "enabled":        body.enabled,
        "trigger_type":   body.trigger_type,
        "trigger_config": body.trigger_config,
        "action_type":    body.action_type,
        "action_config":  body.action_config,
        "last_run":       None,
        "run_count":      0,
        "created_at":     datetime.now(timezone.utc).isoformat(),
    }
    return _insert(row)

@router.put("/{aid}")
def update_automation(aid: str, body: AutomationUpdate):
    changes: dict[str, Any] = {}
    if body.name           is not None: changes["name"]           = body.name
    if body.description    is not None: changes["description"]    = body.description
    if body.enabled        is not None: changes["enabled"]        = body.enabled
    if body.trigger_type   is not None: changes["trigger_type"]   = body.trigger_type
    if body.trigger_config is not None: changes["trigger_config"] = body.trigger_config
    if body.action_type    is not None: changes["action_type"]    = body.action_type
    if body.action_config  is not None: changes["action_config"]  = body.action_config
    row = _update(aid, changes)
    if not row:
        raise HTTPException(status_code=404, detail="Automation not found")
    return row

@router.delete("/{aid}", status_code=204)
def delete_automation(aid: str):
    if not _delete(aid):
        raise HTTPException(status_code=404, detail="Automation not found")

@router.post("/{aid}/run")
async def run_automation(aid: str):
    row = _get(aid)
    if not row:
        raise HTTPException(status_code=404, detail="Automation not found")
    ok, msg = await _run_action(row["action_type"], row.get("action_config") or {})
    _log_run(aid, ok, msg)
    return {"success": ok, "result": msg}

@router.get("/{aid}/logs")
def get_logs(aid: str):
    if not _get(aid):
        raise HTTPException(status_code=404, detail="Automation not found")
    return _get_logs(aid, limit=20)
