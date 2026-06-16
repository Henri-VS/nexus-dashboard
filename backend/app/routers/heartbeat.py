from __future__ import annotations

import asyncio
import logging
import sqlite3
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import yaml
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.core.nexus_dir import nexus_path
from app.routers.notifications import send_notification

logger = logging.getLogger(__name__)
router = APIRouter()

# ── SQLite history store ──────────────────────────────────────────────────────

_DB: Path | None = None


def _db_path() -> Path:
    global _DB
    if _DB is None:
        _DB = Path(settings.db_path).parent / "heartbeat.db"
    return _DB


def _init_db() -> None:
    with sqlite3.connect(_db_path()) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS heartbeat_history (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT    NOT NULL,
                status       TEXT    NOT NULL,
                response_ms  REAL,
                checked_at   TEXT    NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_hb ON heartbeat_history(service_name, checked_at)"
        )
        conn.commit()


def _record(name: str, status: str, response_ms: float | None) -> None:
    checked_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(_db_path()) as conn:
        conn.execute(
            "INSERT INTO heartbeat_history (service_name, status, response_ms, checked_at) VALUES (?, ?, ?, ?)",
            (name, status, response_ms, checked_at),
        )
        # Keep only last 100 rows per service
        conn.execute("""
            DELETE FROM heartbeat_history WHERE id IN (
                SELECT id FROM heartbeat_history
                WHERE service_name = ?
                ORDER BY checked_at DESC
                LIMIT -1 OFFSET 100
            )
        """, (name,))
        conn.commit()


def _query_history(service: str, hours: int = 24) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    with sqlite3.connect(_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT status, response_ms, checked_at FROM heartbeat_history "
            "WHERE service_name = ? AND checked_at > ? ORDER BY checked_at ASC",
            (service, cutoff),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Service registry ──────────────────────────────────────────────────────────

_HEARTBEAT_FILE = "heartbeat.yml"


def _read_user_hosts() -> list[dict]:
    path = nexus_path(_HEARTBEAT_FILE)
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data.get("hosts", [])
    except Exception as exc:
        logger.warning("heartbeat.yml unreadable: %s", exc)
        return []


def _write_user_hosts(hosts: list[dict]) -> None:
    path = nexus_path(_HEARTBEAT_FILE)
    path.write_text(
        yaml.dump({"hosts": hosts}, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def _all_http_services() -> list[dict]:
    auto: list[dict] = []
    if settings.ollama_host:
        auto.append({"name": "Ollama",         "url": settings.ollama_host,    "auto": True})
    if settings.ha_token:
        auto.append({"name": "Home Assistant", "url": settings.ha_url,         "auto": True})
    if settings.wazuh_password:
        auto.append({"name": "Wazuh",          "url": settings.wazuh_api_url,  "auto": True})
    user = [{"auto": False, **h} for h in _read_user_hosts()]
    return auto + user


# ── In-memory current status ──────────────────────────────────────────────────

_status: dict[str, dict] = {}
_last_summary: str = ""


# ── HTTP probe ────────────────────────────────────────────────────────────────

async def _probe_http(name: str, url: str) -> dict:
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=5.0, follow_redirects=True)
        ms  = round((time.monotonic() - t0) * 1000)
        ok  = resp.status_code < 500
        return {"name": name, "status": "up" if ok else "down", "response_ms": ms}
    except Exception as exc:
        logger.debug("probe %s: %s", name, exc)
        return {"name": name, "status": "down", "response_ms": None}


# ── Docker probe ──────────────────────────────────────────────────────────────

def _probe_docker_sync() -> list[dict]:
    try:
        import docker  # type: ignore
        cli = docker.from_env()
        return [
            {
                "name":        f"docker/{c.name}",
                "status":      "up" if c.status == "running" else "down",
                "response_ms": None,
            }
            for c in cli.containers.list(all=True)
        ]
    except Exception as exc:
        logger.debug("docker probe: %s", exc)
        return []


# ── AI summary ────────────────────────────────────────────────────────────────

async def _ai_summary(changes: list[str]) -> str | None:
    if not changes:
        return None
    prompt = (
        f"In one sentence summarise these service changes: {', '.join(changes)}. "
        "Be brief and technical."
    )
    # Try qwen2.5:0.5b first (smallest), fall back silently
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.ollama_host}/api/generate",
                json={"model": "qwen2.5:0.5b", "prompt": prompt, "stream": False},
                timeout=25.0,
            )
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
    except Exception as exc:
        logger.debug("ai_summary: %s", exc)
    return None


# ── Check loop ────────────────────────────────────────────────────────────────

async def _run_checks() -> None:
    global _last_summary

    # Concurrent HTTP probes
    services = _all_http_services()
    http_results: list[dict] = list(
        await asyncio.gather(*[_probe_http(s["name"], s["url"]) for s in services])
    )

    # Docker (blocking, run in thread pool)
    loop = asyncio.get_running_loop()
    docker_results = await loop.run_in_executor(None, _probe_docker_sync)

    all_results = http_results + docker_results
    now         = datetime.now(timezone.utc).isoformat()
    changes: list[str] = []

    for r in all_results:
        name = r["name"]
        prev = _status.get(name, {})

        _record(name, r["status"], r.get("response_ms"))

        if prev.get("status") and prev["status"] != r["status"]:
            verb = "recovered" if r["status"] == "up" else "went down"
            changes.append(f"{name} {verb}")

        _status[name] = {
            **r,
            "last_checked": now,
            "last_seen_up": now if r["status"] == "up" else prev.get("last_seen_up"),
        }

    logger.info(
        "Heartbeat: %d services checked, %d changed", len(all_results), len(changes)
    )

    if changes:
        summary = await _ai_summary(changes)
        if summary:
            _last_summary = summary
        for change in changes:
            event = "recover" if "recovered" in change else "down"
            await send_notification(
                title="Heartbeat Alert",
                message=change,
                feature="heartbeat",
                event=event,
                tags="heartbeat",
            )


async def heartbeat_loop() -> None:
    _init_db()
    logger.info("Heartbeat monitor started — first check running now, then every 15 min")
    # Run immediately on startup so the widget shows data right away
    try:
        await _run_checks()
    except Exception as exc:
        logger.error("heartbeat initial check: %s", exc)
    while True:
        await asyncio.sleep(15 * 60)
        try:
            await _run_checks()
        except Exception as exc:
            logger.error("heartbeat_loop: %s", exc)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status")
async def get_status():
    enriched: dict[str, dict] = {}
    for name, data in _status.items():
        history = _query_history(name, hours=24)
        total   = len(history)
        up_count = sum(1 for h in history if h["status"] == "up")
        uptime_pct = round((up_count / total) * 100) if total else None
        enriched[name] = {**data, "uptime_pct": uptime_pct}

    return {
        "services":     enriched,
        "last_summary": _last_summary,
        "fetched_at":   datetime.now(timezone.utc).isoformat(),
    }


@router.get("/history")
async def get_history(service: str):
    return {
        "service": service,
        "history": _query_history(service, hours=24),
    }


# ── Host management endpoints ─────────────────────────────────────────────────

class HostIn(BaseModel):
    name: str
    url: str


@router.get("/hosts")
async def list_hosts() -> dict:
    """Returns all monitored hosts with auto flag."""
    return {"hosts": _all_http_services()}


@router.post("/hosts")
async def add_host(body: HostIn) -> dict:
    hosts = _read_user_hosts()
    new_id = uuid.uuid4().hex[:8]
    hosts.append({"id": new_id, "name": body.name, "url": body.url})
    _write_user_hosts(hosts)
    return {"ok": True, "id": new_id}


@router.delete("/hosts/{host_id}")
async def remove_host(host_id: str) -> dict:
    hosts = _read_user_hosts()
    hosts = [h for h in hosts if h.get("id") != host_id]
    _write_user_hosts(hosts)
    return {"ok": True}
