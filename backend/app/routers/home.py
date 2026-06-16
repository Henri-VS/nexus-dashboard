import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()

# Domains shown in the widget — ordered by priority
_ALLOWED_DOMAINS = ("switch", "input_boolean", "binary_sensor", "sensor")
_DOMAIN_ORDER    = {d: i for i, d in enumerate(_ALLOWED_DOMAINS)}

# Request timeout for HA calls
_TIMEOUT = httpx.Timeout(5.0)


def _ha_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.ha_token}",
        "Content-Type":  "application/json",
    }


def _domain(entity_id: str) -> str:
    return entity_id.split(".", 1)[0]


@router.get("/entities")
async def get_entities():
    """Return HA entity states filtered to allowed domains, sorted by domain priority.

    Returns an empty list (no error) when HA is not configured or unreachable
    so the frontend can fall back to mock data gracefully.
    """
    if not settings.ha_token:
        return []

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{settings.ha_url}/api/states",
                headers=_ha_headers(),
            )
            resp.raise_for_status()
            all_states = resp.json()
    except Exception:
        return []

    filtered = [
        s for s in all_states
        if _domain(s.get("entity_id", "")) in _ALLOWED_DOMAINS
    ]
    filtered.sort(key=lambda s: _DOMAIN_ORDER.get(_domain(s.get("entity_id", "")), 99))
    return filtered


class ServiceCall(BaseModel):
    domain: str
    service: str
    data: dict = {}


@router.post("/service")
async def call_service(body: ServiceCall):
    """Call a Home Assistant service (e.g. switch toggle).

    Returns an empty dict (no error) when HA is not configured or unreachable.
    """
    if not settings.ha_token:
        return {}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.ha_url}/api/services/{body.domain}/{body.service}",
                headers=_ha_headers(),
                json=body.data,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return {}
