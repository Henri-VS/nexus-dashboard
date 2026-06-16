import logging
import time

import httpx
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# ── 30-second response cache ──────────────────────────────────────────────────
_cache: dict | None = None
_cache_ts: float = 0.0
_CACHE_TTL = 30.0

# ── Mock fallback ─────────────────────────────────────────────────────────────
_MOCK_ALERTS = [
    {
        "id": "1",
        "severity": "CRIT",
        "rule_id": "100010",
        "rule_description": "Rootkit signatures matched on /tmp",
        "rule_level": 15,
        "agent_name": "homelab-server",
        "src_ip": "0.0.0.0",
        "timestamp": "2026-06-07T14:55:02Z",
    },
    {
        "id": "2",
        "severity": "CRIT",
        "rule_id": "5710",
        "rule_description": "SSH brute force — 12 attempts in 60 s",
        "rule_level": 12,
        "agent_name": "homelab-server",
        "src_ip": "203.0.113.42",
        "timestamp": "2026-06-07T14:32:01Z",
    },
    {
        "id": "3",
        "severity": "HIGH",
        "rule_id": "31103",
        "rule_description": "Multiple failed logins (threshold 5)",
        "rule_level": 10,
        "agent_name": "pi-hole",
        "src_ip": "10.0.0.12",
        "timestamp": "2026-06-07T14:28:44Z",
    },
    {
        "id": "4",
        "severity": "HIGH",
        "rule_id": "5715",
        "rule_description": "Port scan detected — 200 ports in 3 s",
        "rule_level": 8,
        "agent_name": "homelab-server",
        "src_ip": "198.51.100.9",
        "timestamp": "2026-06-07T14:15:30Z",
    },
    {
        "id": "5",
        "severity": "HIGH",
        "rule_id": "550",
        "rule_description": "System file integrity check failed — /etc/passwd",
        "rule_level": 8,
        "agent_name": "homelab-server",
        "src_ip": "127.0.0.1",
        "timestamp": "2026-06-07T13:59:18Z",
    },
    {
        "id": "6",
        "severity": "WARN",
        "rule_id": "1002",
        "rule_description": "Syslog error message burst (>50 in 1 min)",
        "rule_level": 6,
        "agent_name": "homelab-server",
        "src_ip": "127.0.0.1",
        "timestamp": "2026-06-07T13:55:18Z",
    },
    {
        "id": "7",
        "severity": "WARN",
        "rule_id": "5402",
        "rule_description": "Successful sudo — privilege escalation",
        "rule_level": 5,
        "agent_name": "homelab-server",
        "src_ip": "192.168.1.10",
        "timestamp": "2026-06-07T13:40:02Z",
    },
    {
        "id": "8",
        "severity": "INFO",
        "rule_id": "5501",
        "rule_description": "User login success via SSH key",
        "rule_level": 3,
        "agent_name": "homelab-server",
        "src_ip": "192.168.1.10",
        "timestamp": "2026-06-07T13:38:55Z",
    },
]


def _level_to_severity(level: int) -> str:
    if level >= 12:
        return "CRIT"
    if level >= 8:
        return "HIGH"
    if level >= 4:
        return "WARN"
    return "INFO"


async def _fetch_alerts() -> list[dict]:
    """Authenticate with Wazuh JWT, then fetch recent alerts."""
    verify = settings.wazuh_verify_ssl
    if not verify:
        logger.warning(
            "Wazuh SSL verification is DISABLED (WAZUH_VERIFY_SSL=false). "
            "Set a valid cert on your Wazuh host to re-enable."
        )
    async with httpx.AsyncClient(verify=verify, timeout=10.0) as client:
        # Step 1: obtain JWT
        auth_resp = await client.get(
            f"{settings.wazuh_api_url}/security/user/authenticate",
            auth=(settings.wazuh_user, settings.wazuh_password),
        )
        auth_resp.raise_for_status()
        token = auth_resp.json()["data"]["token"]

        # Step 2: fetch alerts — newest first, up to 50
        alerts_resp = await client.get(
            f"{settings.wazuh_api_url}/alerts",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": 50, "sort": "-timestamp"},
        )
        alerts_resp.raise_for_status()
        body = alerts_resp.json()

    alerts: list[dict] = []
    for item in body.get("data", {}).get("affected_items", []):
        rule   = item.get("rule", {})
        agent  = item.get("agent", {})
        # Wazuh stores source IP under data.srcip (some versions use src_ip)
        src_ip = (
            item.get("data", {}).get("srcip")
            or item.get("data", {}).get("src_ip")
            or "—"
        )
        level = int(rule.get("level", 0))
        alerts.append(
            {
                "id":               str(item.get("id", "")),
                "severity":         _level_to_severity(level),
                "rule_id":          str(rule.get("id", "")),
                "rule_description": rule.get("description", "Unknown"),
                "rule_level":       level,
                "agent_name":       agent.get("name", "unknown"),
                "src_ip":           src_ip,
                "timestamp":        item.get("timestamp", ""),
            }
        )
    return alerts


@router.get("/alerts")
async def get_alerts():
    """Return recent Wazuh security alerts.

    Returns ``live: true`` when data comes from Wazuh, ``false`` when falling
    back to mock data, so the frontend can show/hide the offline badge.
    """
    global _cache, _cache_ts

    # Serve stale cache while still fresh
    if _cache is not None and time.monotonic() - _cache_ts < _CACHE_TTL:
        return _cache

    # No credentials configured → instant mock, no network attempt
    if not settings.wazuh_user or not settings.wazuh_password:
        return {"live": False, "alerts": _MOCK_ALERTS}

    try:
        alerts = await _fetch_alerts()
        result = {"live": True, "alerts": alerts}
        _cache = result
        _cache_ts = time.monotonic()
        return result
    except Exception:
        # Return stale cache on error rather than crashing
        if _cache is not None:
            return _cache
        return {"live": False, "alerts": _MOCK_ALERTS}
