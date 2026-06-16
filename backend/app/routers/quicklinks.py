from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException

from app.core.ssrf import is_safe_url

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/ping")
async def ping(url: str):
    if not is_safe_url(url):
        raise HTTPException(status_code=400, detail="URL not allowed")
    if not _HAS_HTTPX:
        return {"online": False, "latency_ms": None}
    try:
        async with httpx.AsyncClient() as client:
            t0 = time.monotonic()
            await client.get(url, timeout=3.0, follow_redirects=False)
            return {"online": True, "latency_ms": round((time.monotonic() - t0) * 1000)}
    except Exception as exc:
        logger.debug("ping %s: %s", url, exc)
        return {"online": False, "latency_ms": None}
