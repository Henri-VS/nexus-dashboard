import time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException

from app.core.config import settings

router = APIRouter()

OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"

# Simple in-process cache: {"data": {...}, "ts": float}
_cache: dict = {}
CACHE_TTL = 600  # 10 minutes


def _cache_valid() -> bool:
    return bool(_cache) and (time.monotonic() - _cache["ts"]) < CACHE_TTL


def _day_abbr(date_str: str) -> str:
    """Convert 'YYYY-MM-DD' to 'Mon', 'Tue', etc."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%a")
    except ValueError:
        return date_str


@router.get("")
@router.get("/current")
async def get_current_weather():
    """Return current conditions + 5-day forecast from Open-Meteo (no key required).
    Response is cached for 10 minutes to avoid hammering the free API.
    """
    if _cache_valid():
        return _cache["data"]

    params = {
        "latitude":  settings.weather_lat,
        "longitude": settings.weather_lon,
        "current": ",".join([
            "temperature_2m",
            "weathercode",
            "windspeed_10m",
            "relativehumidity_2m",
            "apparent_temperature",
        ]),
        "daily": "weathercode,temperature_2m_max,temperature_2m_min",
        "timezone": settings.weather_timezone,
        "forecast_days": 5,
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(OPENMETEO_URL, params=params)
            resp.raise_for_status()
            raw = resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=503, detail="weather unavailable") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail="weather unavailable") from exc

    cur = raw["current"]
    daily = raw["daily"]

    # Build 5-day forecast (skip index 0 = today)
    forecast = []
    for i in range(1, min(5, len(daily["time"]))):
        forecast.append({
            "day":  _day_abbr(daily["time"][i]),
            "code": daily["weathercode"][i],
            "high": round(daily["temperature_2m_max"][i], 1),
            "low":  round(daily["temperature_2m_min"][i], 1),
        })

    data = {
        "temperature":          round(cur["temperature_2m"], 1),
        "apparent_temperature": round(cur["apparent_temperature"], 1),
        "weathercode":          cur["weathercode"],
        "windspeed":            round(cur["windspeed_10m"], 1),
        "humidity":             cur["relativehumidity_2m"],
        "location":             settings.weather_location_name,
        "forecast":             forecast,
    }

    _cache["data"] = data
    _cache["ts"]   = time.monotonic()
    return data
