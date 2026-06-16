from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks

from app.core import rag as rag_core

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status")
async def rag_status():
    """RAG system status: available, indexed chunk count, collection name."""
    return await rag_core.status()


@router.post("/ingest")
async def trigger_ingest(background_tasks: BackgroundTasks):
    """
    Manually trigger a full re-index of all sources (automations, notes, vault).
    Returns immediately; indexing runs in the background.
    """
    background_tasks.add_task(_run_ingest)
    return {"message": "Re-index started in background"}


async def _run_ingest() -> None:
    try:
        result = await rag_core.ingest_all()
        logger.info("Manual re-index complete: %s", result)
    except Exception as exc:
        logger.error("Re-index failed: %s", exc)
