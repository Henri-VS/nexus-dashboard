import os
from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()

# Status sort order: running first
_STATUS_ORDER = {"running": 0, "restarting": 1, "paused": 2, "exited": 3}


def _uptime(started_at_str: str) -> str:
    """Convert Docker's StartedAt ISO string to a human-readable uptime.
    Returns '—' if the container is not running / timestamp is zero.
    """
    if not started_at_str or started_at_str.startswith("0001"):
        return "—"
    try:
        # Docker returns e.g. '2024-01-15T10:23:00.123456789Z'
        # Strip nanoseconds down to microseconds for fromisoformat compat
        ts = started_at_str[:26].rstrip("Z")
        started = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
        delta   = datetime.now(timezone.utc) - started
        total_s = int(delta.total_seconds())

        days    = total_s // 86_400
        hours   = (total_s % 86_400) // 3_600
        minutes = (total_s % 3_600)  // 60

        if days:
            return f"{days}d {hours}h"
        if hours:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except Exception:
        return "—"


def _health(container_attrs: dict) -> str:
    state  = container_attrs.get("State", {})
    health = state.get("Health", {})
    if not health:
        return "none"
    return health.get("Status", "none")


@router.get("")
@router.get("/containers")
async def get_containers():
    """Return all Docker containers sorted running-first.
    If the Docker socket is unavailable the endpoint returns an empty list
    with docker_unavailable=true rather than raising a 502.
    """
    try:
        import docker as docker_sdk  # noqa: PLC0415 — lazy import so missing SDK doesn't break startup
        base_url = os.environ.get("DOCKER_HOST", "unix:///var/run/docker.sock")
        client = docker_sdk.DockerClient(base_url=base_url, timeout=5)
        containers = client.containers.list(all=True)
    except Exception:
        # Docker not available (socket missing, daemon down, SDK not installed)
        return {"docker_unavailable": True, "containers": []}

    result = []
    for c in containers:
        try:
            image_tag = c.image.tags[0] if c.image.tags else c.image.short_id
        except Exception:
            image_tag = "unknown"

        started_at = c.attrs.get("State", {}).get("StartedAt", "")
        restart_count = c.attrs.get("RestartCount", 0)

        result.append({
            "id":            c.short_id,
            "name":          c.name,
            "image":         image_tag,
            "status":        c.status,
            "health":        _health(c.attrs),
            "uptime":        _uptime(started_at),
            "restart_count": restart_count,
        })

    result.sort(key=lambda c: _STATUS_ORDER.get(c["status"], 99))
    return {"docker_unavailable": False, "containers": result}
