from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# ── SQLModel model (schema registered via database.py init_db) ────────────────

class LogEntry(SQLModel, table=True):
    __tablename__ = "log_entries"
    id:          Optional[int] = Field(default=None, primary_key=True)
    ts:          str           = Field(index=True)
    level:       str           = Field(index=True)
    source:      str           = Field(index=True)
    message:     str
    logger_name: str           = Field(default="")

# ── Raw SQLite helpers (same db path as SQLModel engine) ──────────────────────

def _db_path() -> str:
    return settings.db_path

def _insert_raw(ts: str, level: str, source: str, message: str, logger_name: str = "") -> None:
    try:
        with sqlite3.connect(_db_path()) as conn:
            conn.execute(
                "INSERT INTO log_entries (ts, level, source, message, logger_name) VALUES (?,?,?,?,?)",
                (ts, level, source, message, logger_name),
            )
            conn.execute("""
                DELETE FROM log_entries WHERE id IN (
                    SELECT id FROM log_entries ORDER BY id DESC LIMIT -1 OFFSET 10000
                )
            """)
            conn.commit()
    except Exception:
        pass  # never let log storage crash the app

def _query_raw(source: str | None, level: str | None, limit: int) -> list[dict]:
    clauses: list[str] = []
    params: list = []
    if source:
        clauses.append("source = ?")
        params.append(source)
    if level:
        lvl = level.upper()
        if lvl in ("WARN", "WARNING"):
            clauses.append("level IN ('WARN','WARNING')")
        else:
            clauses.append("level = ?")
            params.append(lvl)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)
    with sqlite3.connect(_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"SELECT id, ts, level, source, message, logger_name "
            f"FROM log_entries {where} ORDER BY id DESC LIMIT ?",
            params,
        ).fetchall()
    return [dict(r) for r in reversed(rows)]

# ── SSE broadcast ─────────────────────────────────────────────────────────────

_subscribers: list[asyncio.Queue] = []

def _broadcast(entry: dict) -> None:
    dead = []
    for q in _subscribers:
        try:
            q.put_nowait(entry)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        try:
            _subscribers.remove(q)
        except ValueError:
            pass

# ── Python logging capture ────────────────────────────────────────────────────

class _BackendLogCapture(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            ts  = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
            lvl = record.levelname
            msg = self.format(record)
            _insert_raw(ts, lvl, "backend", msg, record.name)
            entry = {"ts": ts, "level": lvl, "source": "backend", "message": msg, "logger_name": record.name}
            try:
                loop = asyncio.get_running_loop()
                loop.call_soon_threadsafe(_broadcast, entry)
            except RuntimeError:
                pass
        except Exception:
            pass

_capture_handler: _BackendLogCapture | None = None

def _attach_log_capture() -> None:
    global _capture_handler
    if _capture_handler is not None:
        return
    _capture_handler = _BackendLogCapture()
    _capture_handler.setLevel(logging.DEBUG)
    _capture_handler.setFormatter(logging.Formatter("%(name)s — %(message)s"))
    logging.getLogger().addHandler(_capture_handler)

# ── Docker log streaming ──────────────────────────────────────────────────────

_docker_tasks: dict[str, asyncio.Task] = {}

async def _stream_container(name: str, cid: str) -> None:
    try:
        import docker  # type: ignore
        loop = asyncio.get_running_loop()
        cli  = docker.from_env()

        def _start():
            container = cli.containers.get(cid)
            return container.logs(stream=True, follow=True, since=int(time.time()) - 60, timestamps=True)

        log_iter = await loop.run_in_executor(None, _start)

        def _next():
            try:
                return next(log_iter)
            except StopIteration:
                return None

        while True:
            raw = await loop.run_in_executor(None, _next)
            if raw is None:
                break
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            ts  = datetime.now(timezone.utc).isoformat()
            lc  = line.lower()
            lvl = ("ERROR" if any(w in lc for w in ("error", "exception", "fatal", "critical")) else
                   "WARN"  if any(w in lc for w in ("warn", "warning")) else "INFO")
            source = f"docker/{name}"
            _insert_raw(ts, lvl, source, line)
            _broadcast({"ts": ts, "level": lvl, "source": source, "message": line, "logger_name": ""})

    except asyncio.CancelledError:
        return
    except Exception as exc:
        logger.debug("container log stream %s: %s", name, exc)

# ── Lifecycle (called from main.py lifespan) ──────────────────────────────────

async def start_log_capture() -> None:
    _attach_log_capture()
    try:
        import docker  # type: ignore
        loop = asyncio.get_running_loop()
        cli  = docker.from_env()
        containers = await loop.run_in_executor(None, lambda: cli.containers.list())
        for c in containers:
            if c.name not in _docker_tasks:
                task = asyncio.create_task(_stream_container(c.name, c.id))
                _docker_tasks[c.name] = task
        logger.info("Log capture started — streaming %d Docker containers", len(containers))
    except Exception as exc:
        logger.debug("docker log init: %s", exc)

def stop_log_capture() -> None:
    for t in _docker_tasks.values():
        t.cancel()
    _docker_tasks.clear()
    global _capture_handler
    if _capture_handler is not None:
        logging.getLogger().removeHandler(_capture_handler)
        _capture_handler = None

# ── SSE stream endpoint ───────────────────────────────────────────────────────

@router.get("/stream")
async def stream_logs():
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _subscribers.append(q)

    async def gen() -> AsyncGenerator[str, None]:
        try:
            while True:
                try:
                    entry = await asyncio.wait_for(q.get(), timeout=25.0)
                    yield f"event: log\ndata: {json.dumps(entry)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            return
        finally:
            try:
                _subscribers.remove(q)
            except ValueError:
                pass

    return StreamingResponse(gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })

# ── History endpoint ──────────────────────────────────────────────────────────

@router.get("/history")
async def get_history(source: str | None = None, level: str | None = None, limit: int = 500):
    return {"entries": _query_raw(source, level, min(limit, 2000))}

# ── Custom log POST endpoint ──────────────────────────────────────────────────

class _CustomLogBody(BaseModel):
    level:   str
    source:  str
    message: str

@router.post("/custom")
async def post_custom(body: _CustomLogBody):
    ts  = datetime.now(timezone.utc).isoformat()
    lvl = body.level.upper()
    entry = {"ts": ts, "level": lvl, "source": body.source, "message": body.message, "logger_name": ""}
    _insert_raw(ts, lvl, body.source, body.message)
    _broadcast(entry)
    return {"ok": True}
