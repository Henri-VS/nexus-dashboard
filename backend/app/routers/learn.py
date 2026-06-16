import asyncio
import logging
import time
from datetime import date

import httpx
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_session
from app.models.learn import CertTracker

router = APIRouter()
logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(10.0)

_MOCK_THM = {
    "thm_rank":            "Hacker",
    "thm_points":          12_450,
    "thm_completed_rooms": 44,
    "badge_name":          "",
    "streak":              0,
}

# ── Response cache ─────────────────────────────────────────────────────────────
_thm_cache: dict | None = None
_thm_cache_ts: float = 0.0
_THM_CACHE_TTL = 300.0  # 5 minutes

# ── THM fetch ─────────────────────────────────────────────────────────────────


async def _fetch_thm(username: str) -> dict:
    """Fetch rank and badges concurrently. Returns merged data dict."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        rank_task   = client.get(f"https://tryhackme.com/api/user/rank/{username}")
        badges_task = client.get(
            f"https://tryhackme.com/api/no-auth/user/{username}/badges"
        )
        rank_resp, badges_resp = await asyncio.gather(
            rank_task, badges_task, return_exceptions=True
        )

    rank: dict = {}
    if isinstance(rank_resp, httpx.Response) and rank_resp.status_code == 200:
        try:
            rank = rank_resp.json()
        except Exception:
            pass

    badge_name = ""
    if isinstance(badges_resp, httpx.Response) and badges_resp.status_code == 200:
        try:
            body = badges_resp.json()
            # API returns either a bare list or {"data": [...]}
            badge_list: list = body if isinstance(body, list) else body.get("data", [])
            if badge_list:
                badge_name = badge_list[0].get("name", "")
        except Exception:
            pass

    # THM uses several field names for streak across API versions
    streak = (
        rank.get("currentStreak")
        or rank.get("streak")
        or rank.get("dailyStreak")
        or 0
    )

    # THM has used both camelCase and snake_case across API versions
    completed_rooms = (
        rank.get("completed_rooms")
        or rank.get("completedRooms")
        or 0
    )

    return {
        "thm_rank":            rank.get("userRank", "—"),
        "thm_points":          rank.get("points", 0),
        "thm_completed_rooms": completed_rooms,
        "badge_name":          badge_name,
        "streak":              streak,
    }


# ── Endpoint ──────────────────────────────────────────────────────────────────


@router.get("/progress")
async def get_progress(session: Session = Depends(get_session)):
    """Return THM profile data + cert trackers from DB.

    Falls back to the last cached response when the THM API is unreachable, and
    to static mock data when no cache exists yet.
    """
    global _thm_cache, _thm_cache_ts

    username = settings.thm_username or ""

    # Serve from cache if still fresh
    if _thm_cache is not None and time.monotonic() - _thm_cache_ts < _THM_CACHE_TTL:
        thm = _thm_cache
    elif not username:
        thm = _thm_cache if _thm_cache is not None else _MOCK_THM.copy()
    else:
        try:
            thm = await _fetch_thm(username)
            # Only promote to cache when we received meaningful data
            if thm["thm_points"] > 0 or thm["thm_rank"] not in ("—", ""):
                _thm_cache = thm
                _thm_cache_ts = time.monotonic()
            elif _thm_cache is not None:
                logger.info("THM returned empty data for %r — using cached response", username)
                thm = _thm_cache
        except Exception as exc:
            logger.warning("THM API fetch failed for user %r: %s", username, exc)
            thm = _thm_cache if _thm_cache is not None else _MOCK_THM.copy()

    certs = session.exec(select(CertTracker)).all()
    today = date.today()
    cert_list = []
    for cert in certs:
        days = (cert.exam_date - today).days if cert.exam_date else None
        cert_list.append({
            "name":           cert.name,
            "exam_date":      cert.exam_date.isoformat() if cert.exam_date else None,
            "days_remaining": days,
            "status":         cert.status,
        })

    return {**thm, "certs": cert_list}
