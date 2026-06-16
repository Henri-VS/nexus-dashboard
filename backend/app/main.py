import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import init_db
from app.core.nexus_dir import ensure_nexus_dirs
from app.core import rag as rag_core
from app.routers import ai, automations, calendar, docker, heartbeat, home, learn, logs, news, nexus_config, notes, notifications, quicklinks, rag as rag_router, resources, security, services_catalog, system, weather

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.nexus_secret_key:
        logger.warning("NEXUS_SECRET_KEY is not set — authentication is DISABLED (dev mode)")
    if not rag_core._CHROMA_AVAILABLE:
        logger.warning("chromadb not installed — RAG disabled. Run: pip install chromadb")
    ensure_nexus_dirs()
    init_db()
    automations.migrate_automations_from_sqlite()
    cal_task  = asyncio.create_task(calendar.reminder_loop())
    hb_task   = asyncio.create_task(heartbeat.heartbeat_loop())
    auto_task = asyncio.create_task(automations.schedule_loop())
    asyncio.create_task(rag_core.ingest_all())   # fire-and-forget; fails silently
    await logs.start_log_capture()
    yield
    logs.stop_log_capture()
    cal_task.cancel()
    hb_task.cancel()
    auto_task.cancel()
    with suppress(asyncio.CancelledError):
        await cal_task
    with suppress(asyncio.CancelledError):
        await hb_task
    with suppress(asyncio.CancelledError):
        await auto_task


app = FastAPI(
    title="Nexus API",
    version="0.1.0",
    docs_url="/docs" if not settings.nexus_secret_key else None,
    redoc_url=None,
    lifespan=lifespan,
)

_cors_origins = ["http://localhost:3000", "http://localhost:5173", "http://frontend:3000"]
if settings.nexus_frontend_url:
    _cors_origins.append(settings.nexus_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _auth_middleware(request: Request, call_next):
    # Skip CORS preflight and unauthenticated routes
    if request.method == "OPTIONS" or not request.url.path.startswith("/api/"):
        return await call_next(request)
    if settings.nexus_secret_key:
        auth = request.headers.get("Authorization", "")
        token = auth[7:] if auth.startswith("Bearer ") else None
        if token != settings.nexus_secret_key:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "auth_enabled": bool(settings.nexus_secret_key)}


# ── Routers ──────────────────────────────────────────────────
app.include_router(weather.router,  prefix="/api/weather",   tags=["weather"])
app.include_router(system.router,   prefix="/api/system",    tags=["system"])
app.include_router(security.router, prefix="/api/security",  tags=["security"])
app.include_router(docker.router,   prefix="/api/docker",    tags=["docker"])
app.include_router(notes.router,    prefix="/api/notes",     tags=["notes"])
app.include_router(home.router,     prefix="/api/home",      tags=["home"])
app.include_router(learn.router,    prefix="/api/learn",     tags=["learn"])
app.include_router(ai.router,       prefix="/api/ai",        tags=["ai"])
app.include_router(calendar.router,  prefix="/api/calendar",   tags=["calendar"])
app.include_router(resources.router, prefix="/api/resources",  tags=["resources"])
app.include_router(news.router,       prefix="/api/news",       tags=["news"])
app.include_router(quicklinks.router,  prefix="/api/quicklinks",  tags=["quicklinks"])
app.include_router(heartbeat.router,   prefix="/api/heartbeat",   tags=["heartbeat"])
app.include_router(logs.router,        prefix="/api/logs",        tags=["logs"])
app.include_router(automations.router,     prefix="/api/automations",     tags=["automations"])
app.include_router(notifications.router,   prefix="/api/notifications",   tags=["notifications"])
app.include_router(nexus_config.router,    prefix="/api/nexus",           tags=["nexus"])
app.include_router(rag_router.router,      prefix="/api/rag",             tags=["rag"])
app.include_router(services_catalog.router, prefix="/api/services",       tags=["services"])
