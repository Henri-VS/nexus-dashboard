"""
User-configurable service catalog.
Services are stored in .nexus/services.yml as a list under the key "services".
Each service: id, name, url, category, icon (lucide name), description, enabled.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

import httpx
import yaml
from fastapi import APIRouter, HTTPException

from app.core.ssrf import is_safe_url
from pydantic import BaseModel

from app.core.nexus_dir import nexus_path

logger = logging.getLogger(__name__)
router = APIRouter()

_SERVICES_FILE = "services.yml"


def _read() -> list[dict[str, Any]]:
    path = nexus_path(_SERVICES_FILE)
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data.get("services", [])
    except Exception as exc:
        logger.warning("Cannot read services.yml: %s", exc)
        return []


def _write(services: list[dict[str, Any]]) -> None:
    path = nexus_path(_SERVICES_FILE)
    path.write_text(
        yaml.dump({"services": services}, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


class ServiceIn(BaseModel):
    name: str
    url: str
    category: str = "Other"
    icon: str = "globe"
    description: str = ""
    enabled: bool = True


class ReorderBody(BaseModel):
    ids: list[str]


@router.get("")
async def list_services() -> dict[str, list[dict[str, Any]]]:
    return {"services": _read()}


@router.post("")
async def create_service(body: ServiceIn) -> dict[str, Any]:
    services = _read()
    new_id = uuid.uuid4().hex[:8]
    service: dict[str, Any] = {"id": new_id, **body.model_dump()}
    services.append(service)
    _write(services)
    return service


@router.get("/ping")
async def ping_service(url: str) -> dict[str, Any]:
    if not is_safe_url(url):
        raise HTTPException(status_code=400, detail="URL not allowed")
    try:
        async with httpx.AsyncClient(timeout=3.0, follow_redirects=False) as client:
            t0 = time.monotonic()
            resp = await client.get(url)
            ms = round((time.monotonic() - t0) * 1000)
            return {"online": resp.status_code < 500, "latency_ms": ms}
    except Exception:
        return {"online": False, "latency_ms": None}


@router.put("/{service_id}")
async def update_service(service_id: str, body: ServiceIn) -> dict[str, Any]:
    all_services = _read()
    for i, s in enumerate(all_services):
        if s.get("id") == service_id:
            all_services[i] = {"id": service_id, **body.model_dump()}
            _write(all_services)
            return all_services[i]
    return {"error": "not found"}


@router.delete("/{service_id}")
async def delete_service(service_id: str) -> dict[str, bool]:
    services = _read()
    services = [s for s in services if s.get("id") != service_id]
    _write(services)
    return {"ok": True}


@router.post("/reorder")
async def reorder_services(body: ReorderBody) -> dict[str, bool]:
    services = _read()
    lookup = {s["id"]: s for s in services if "id" in s}
    reordered = [lookup[i] for i in body.ids if i in lookup]
    seen = {s["id"] for s in reordered}
    for s in services:
        if s.get("id") not in seen:
            reordered.append(s)
    _write(reordered)
    return {"ok": True}
