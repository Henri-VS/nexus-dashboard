from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from fastapi import APIRouter
from pydantic import BaseModel
import yaml
from app.core.nexus_dir import nexus_path

try:
    import feedparser
    _HAS_FEEDPARSER = True
except ImportError:
    _HAS_FEEDPARSER = False

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Feed registry ─────────────────────────────────────────────────────────────

_FEEDS_FILE = "feeds.yml"

_DEFAULT_FEEDS: list[dict] = [
    {"url": "https://feeds.feedburner.com/TheHackersNews",              "source": "The Hacker News",  "category": "Security",     "enabled": True},
    {"url": "https://www.bleepingcomputer.com/feed/",                   "source": "Bleeping Computer","category": "Security",     "enabled": True},
    {"url": "https://www.darkreading.com/rss.xml",                      "source": "Dark Reading",     "category": "Security",     "enabled": True},
    {"url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "source": "Ars Technica",     "category": "Tech",         "enabled": True},
    {"url": "https://spectrum.ieee.org/feeds/feed.rss",                 "source": "IEEE Spectrum",    "category": "Robotics",     "enabled": True},
    {"url": "https://selfh.st/rss/",                                    "source": "selfh.st",         "category": "Self-hosted",  "enabled": True},
]


def _read_feeds() -> list[dict]:
    path = nexus_path(_FEEDS_FILE)
    if not path.exists():
        return _DEFAULT_FEEDS
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data.get("feeds", _DEFAULT_FEEDS)
    except Exception:
        return _DEFAULT_FEEDS


def _write_feeds(feeds: list[dict]) -> None:
    path = nexus_path(_FEEDS_FILE)
    path.write_text(
        yaml.dump({"feeds": feeds}, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NexusDashboard/1.0)",
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
}

# ── Scoring keywords ──────────────────────────────────────────────────────────

_HIGH_VALUE_TERMS = {
    "ai", "artificial intelligence", "breakthrough", "critical", "zero-day",
    "zero day", "vulnerability", "exploit", "robot", "robotics", "gpt", "claude",
    "gemini", "llm", "major", "hack", "hacked", "breach", "ransomware",
    "generative", "autonomous", "humanoid",
}

_PREMIUM_SOURCES = {"IEEE Spectrum", "Ars Technica", "Ars Technica AI", "TechCrunch", "Krebs on Security", "Schneier", "OpenAI Blog", "Anthropic Blog"}

# ── In-memory cache ───────────────────────────────────────────────────────────

_cache: dict = {"articles": [], "fetched_at": 0.0, "failed_feeds": 0}
_CACHE_TTL   = 60 * 60  # 60 minutes

# ── Mock fallback ─────────────────────────────────────────────────────────────

_MOCK_ARTICLES = [
    {
        "title":     "News feeds unavailable — backend running but feeds timed out",
        "link":      "https://github.com/",
        "summary":   "All configured RSS feeds failed to respond. Check network connectivity from the backend container and review logs for per-feed errors.",
        "source":    "System",
        "published": datetime.now(tz=timezone.utc).isoformat(),
        "category":  "tech",
        "score":     0,
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────

_TAG_RE  = re.compile(r"<[^>]+>")
_WS_RE   = re.compile(r"\s+")

def _strip_html(text: str) -> str:
    text = _TAG_RE.sub(" ", text or "")
    text = _WS_RE.sub(" ", text).strip()
    return text


def _clean_summary(raw: str) -> str:
    cleaned = _strip_html(raw)
    if len(cleaned) > 200:
        cleaned = cleaned[:197].rsplit(" ", 1)[0] + "…"
    return cleaned


def _parse_date(entry: object) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                return parsedate_to_datetime(raw).astimezone(timezone.utc)
            except Exception:
                pass
    return None


def _score(title: str, summary: str, source: str) -> int:
    score = 0
    combined = (title + " " + summary).lower()

    # +3 per high-value keyword in title/summary
    for term in _HIGH_VALUE_TERMS:
        if term in combined:
            score += 3

    # +2 premium source bonus
    if source in _PREMIUM_SOURCES:
        score += 2

    # +1 per word in summary (longer = more substantial)
    word_count = len(summary.split())
    score += min(word_count, 30)  # cap at 30 to avoid runaway scores

    return score


_AI_TERMS = {
    "ai", "artificial intelligence", "machine learning", "llm", "gpt", "claude",
    "gemini", "llama", "neural", " model", "chatbot", "openai", "anthropic",
    "deep learning", "automation", "generative",
}
_ROBOT_TERMS = {
    "robot", "robotics", "drone", "autonomous", "humanoid",
    "boston dynamics", "mechanical", "actuator",
}
_CYBER_TERMS = {
    "hack", "hacked", "vulnerability", "exploit", "breach", "malware",
    "ransomware", "cve", "zero-day", "zero day", "phishing", "security",
}
_CYBER_SOURCES = {
    "the hacker news", "bleepingcomputer", "krebs on security",
    "dark reading", "schneier", "threatpost", "the register",
}


def _detect_category(title: str, summary: str, feed_source: str, feed_default: str) -> str:
    combined = (title + " " + summary).lower()
    source_lc = feed_source.lower()

    if any(t in combined for t in _AI_TERMS):
        return "ai"
    if any(t in combined for t in _ROBOT_TERMS):
        return "robotics"
    if any(s in source_lc for s in _CYBER_SOURCES) or any(t in combined for t in _CYBER_TERMS):
        return "cybersecurity"
    return feed_default  # tech / robotics as declared in FEEDS


def _parse_entries(raw_content: str, feed_def: dict, cutoff: datetime) -> list[dict]:
    parsed = feedparser.parse(raw_content)
    articles = []
    for entry in parsed.entries[:20]:
        title   = _strip_html(getattr(entry, "title", ""))
        link    = getattr(entry, "link", "") or ""
        if not title or not link:
            continue

        pub_dt = _parse_date(entry)
        if pub_dt is None or pub_dt < cutoff:
            continue

        raw_summary = (
            getattr(entry, "summary", "")
            or getattr(entry, "description", "")
            or ""
        )
        summary  = _clean_summary(raw_summary)
        source   = feed_def["source"]
        category = _detect_category(title, summary, source, feed_def["category"])

        articles.append({
            "title":     title,
            "link":      link,
            "summary":   summary,
            "source":    source,
            "published": pub_dt.isoformat(),
            "category":  category,
            "score":     _score(title, summary, source),
        })
    return articles


# ── Async fetch ───────────────────────────────────────────────────────────────

async def _fetch_one(client: "httpx.AsyncClient", feed_def: dict, cutoff: datetime) -> list[dict]:
    url = feed_def["url"]
    try:
        resp = await client.get(url, timeout=10.0)
        resp.raise_for_status()
        articles = _parse_entries(resp.text, feed_def, cutoff)
        logger.info("Feed OK  %-32s  %d articles (last 24-48h)", feed_def["source"], len(articles))
        return articles
    except Exception as exc:
        logger.warning("Feed FAIL %-30s  %s: %s", feed_def["source"], type(exc).__name__, exc)
        return []


async def _fetch_all(cutoff: datetime) -> tuple[list[dict], int]:
    """Returns (articles, failed_feed_count)."""
    active_feeds = [f for f in _read_feeds() if f.get("enabled", True)]

    if not _HAS_HTTPX:
        logger.error("httpx not installed")
        return _MOCK_ARTICLES[:], len(active_feeds)

    async with httpx.AsyncClient(headers=_HEADERS, follow_redirects=True) as client:
        chunks = await asyncio.gather(*[_fetch_one(client, fd, cutoff) for fd in active_feeds])

    failed = sum(1 for chunk in chunks if not chunk)

    all_articles: list[dict] = []
    for chunk in chunks:
        all_articles.extend(chunk)

    if not all_articles:
        logger.error("All %d feeds returned 0 articles — returning mock", len(active_feeds))
        return _MOCK_ARTICLES[:], len(active_feeds)

    # Sort by score desc, then by date desc as tiebreaker
    all_articles.sort(key=lambda a: (a["score"], a["published"]), reverse=True)
    logger.info("Total %d articles after scoring, returning top 30 (%d feeds failed)", len(all_articles), failed)
    return all_articles[:30], failed


async def _fetch_with_window() -> tuple[list[dict], int]:
    """Try 24h window first; extend to 48h if fewer than 10 real articles."""
    now = datetime.now(tz=timezone.utc)

    cutoff_24h = now - timedelta(hours=24)
    articles, failed = await _fetch_all(cutoff_24h)

    real = [a for a in articles if a.get("source") != "System"]
    if len(real) < 10:
        logger.info("Only %d articles in 24h window — extending to 48h", len(real))
        cutoff_48h = now - timedelta(hours=48)
        articles, failed = await _fetch_all(cutoff_48h)

    return articles, failed


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get("")
async def get_news(refresh: bool = False):
    if not _HAS_FEEDPARSER:
        logger.error("feedparser not installed")
        return {
            "error":        "feedparser not installed — run: pip install feedparser",
            "articles":     _MOCK_ARTICLES,
            "fetched_at":   datetime.now(tz=timezone.utc).isoformat(),
            "count":        len(_MOCK_ARTICLES),
            "failed_feeds": len(_read_feeds()),
        }

    now   = time.monotonic()
    stale = (now - _cache["fetched_at"]) > _CACHE_TTL

    if refresh or stale or not _cache["articles"]:
        try:
            articles, failed_feeds = await asyncio.wait_for(_fetch_with_window(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.error("Feed fetch timed out after 30s — returning mock")
            articles, failed_feeds = _MOCK_ARTICLES[:], len(_read_feeds())
        _cache["articles"]      = articles
        _cache["failed_feeds"]  = failed_feeds
        _cache["fetched_at"]    = now

    fetched_wall = time.time() - (now - _cache["fetched_at"])
    return {
        "articles":     _cache["articles"],
        "fetched_at":   datetime.fromtimestamp(fetched_wall, tz=timezone.utc).isoformat(),
        "count":        len(_cache["articles"]),
        "failed_feeds": _cache.get("failed_feeds", 0),
    }


# ── Feed management endpoints ─────────────────────────────────────────────────

class FeedIn(BaseModel):
    url: str
    source: str
    category: str = "general"
    enabled: bool = True


@router.get("/feeds")
async def list_feeds() -> dict:
    return {"feeds": _read_feeds()}


@router.post("/feeds")
async def add_feed(body: FeedIn) -> dict:
    feeds = _read_feeds()
    if any(f["url"] == body.url for f in feeds):
        return {"error": "Feed URL already exists"}
    feeds.append(body.model_dump())
    _write_feeds(feeds)
    return {"ok": True, "feeds": feeds}


@router.delete("/feeds")
async def remove_feed(url: str) -> dict:
    feeds = _read_feeds()
    feeds = [f for f in feeds if f["url"] != url]
    _write_feeds(feeds)
    return {"ok": True}


@router.patch("/feeds")
async def toggle_feed(url: str, enabled: bool) -> dict:
    feeds = _read_feeds()
    for f in feeds:
        if f["url"] == url:
            f["enabled"] = enabled
    _write_feeds(feeds)
    return {"ok": True}


@router.post("/feeds/reset")
async def reset_feeds() -> dict:
    """Reset to the built-in default feed list."""
    _write_feeds(_DEFAULT_FEEDS)
    return {"ok": True, "feeds": _DEFAULT_FEEDS}
