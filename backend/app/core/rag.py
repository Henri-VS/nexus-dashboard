"""
RAG module for Nexus Dashboard.

Uses ChromaDB in embedded mode + Ollama /api/embeddings (nomic-embed-text).
All operations fail silently — RAG is a best-effort enhancement to AI chat,
never a blocking dependency.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import httpx

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    _CHROMA_AVAILABLE = True
except ImportError:
    chromadb = None  # type: ignore
    ChromaSettings = None  # type: ignore
    _CHROMA_AVAILABLE = False

from app.core.config import settings as nexus_settings
from app.core.nexus_dir import nexus_path

logger = logging.getLogger(__name__)

COLLECTION_NAME = "nexus_docs"
EMBED_MODEL     = "nomic-embed-text"
CHUNK_SIZE      = 800
CHUNK_OVERLAP   = 150
MIN_SCORE       = 0.30
TOP_K           = 5

_client: Any     = None
_collection: Any = None


def _get_client() -> tuple[Any, Any]:
    """Lazy-init ChromaDB. Returns (client, collection) or (None, None) on failure."""
    global _client, _collection
    if not _CHROMA_AVAILABLE:
        return None, None
    if _client is not None:
        return _client, _collection
    try:
        data_dir = Path(nexus_settings.nexus_data_dir) / ".chroma"
        data_dir.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(data_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB initialised at %s", data_dir)
        return _client, _collection
    except Exception as exc:
        logger.warning("ChromaDB init failed (RAG disabled): %s", exc)
        return None, None


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter (--- ... ---) from markdown content."""
    return re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL).strip()


def _chunk(text: str) -> list[str]:
    """Split text into overlapping chunks of CHUNK_SIZE with CHUNK_OVERLAP."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + CHUNK_SIZE])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c.strip() for c in chunks if c.strip()]


async def _embed(texts: list[str]) -> list[list[float]] | None:
    """Call Ollama /api/embeddings for each text. Returns embedding vectors or None."""
    embeddings: list[list[float]] = []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for text in texts:
                resp = await client.post(
                    f"{nexus_settings.ollama_host}/api/embeddings",
                    json={"model": EMBED_MODEL, "prompt": text},
                )
                if resp.status_code != 200:
                    logger.debug("Embedding request returned %s", resp.status_code)
                    return None
                data = resp.json()
                embeddings.append(data["embedding"])
        return embeddings
    except Exception as exc:
        logger.debug("Embedding call failed: %s", exc)
        return None


async def ingest_file(path: Path, source_label: str | None = None) -> int:
    """
    Ingest a single file into ChromaDB.
    Returns number of chunks indexed (0 on any failure).
    """
    _, collection = _get_client()
    if collection is None:
        return 0

    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Cannot read %s: %s", path, exc)
        return 0

    content = _strip_frontmatter(raw)
    if not content:
        return 0

    chunks = _chunk(content)
    if not chunks:
        return 0

    label = source_label or path.name

    # Delete stale chunks for this source before re-indexing
    try:
        existing = collection.get(where={"source": label})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass  # collection may be empty — harmless

    embeddings = await _embed(chunks)
    if embeddings is None:
        return 0

    ids = [f"{label}::chunk{i}" for i in range(len(chunks))]
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=[{"source": label, "file": str(path)} for _ in chunks],
    )
    logger.info("Indexed %d chunks from %s", len(chunks), label)
    return len(chunks)


async def ingest_all() -> dict:
    """Ingest all discoverable sources. Called on startup (non-blocking)."""
    # ── Check Ollama is reachable before attempting to embed anything ──
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{nexus_settings.ollama_host}/api/tags")
            if r.status_code != 200:
                raise ValueError(f"status {r.status_code}")
    except Exception as exc:
        logger.info(
            "RAG ingest skipped — Ollama not reachable at %s (%s). "
            "RAG will be available once Ollama is running.",
            nexus_settings.ollama_host, exc,
        )
        return {"indexed_chunks": 0, "sources": [], "skipped": True}

    # ── Check ChromaDB is available ────────────────────────────────────
    _, collection = _get_client()
    if collection is None:
        logger.info("RAG ingest skipped — ChromaDB unavailable.")
        return {"indexed_chunks": 0, "sources": [], "skipped": True}

    sources_indexed: list[str] = []
    total_chunks = 0

    # 1. .nexus/automations/*.md
    auto_dir = nexus_path("automations")
    if auto_dir.is_dir():
        for p in sorted(auto_dir.glob("*.md")):
            n = await ingest_file(p, f"automation:{p.stem}")
            if n:
                sources_indexed.append(p.name)
                total_chunks += n

    # 2. .nexus/notes/*.md (optional — created by users, not always present)
    notes_dir = nexus_path("notes")
    if notes_dir.is_dir():
        for p in sorted(notes_dir.rglob("*.md")):
            n = await ingest_file(p, f"note:{p.stem}")
            if n:
                sources_indexed.append(p.name)
                total_chunks += n

    # 3. Obsidian vault (OBSIDIAN_VAULT_PATH — only if directory exists)
    vault = Path(nexus_settings.obsidian_vault_path)
    if vault.is_dir():
        for p in sorted(vault.rglob("*.md"))[:200]:  # cap at 200 files
            n = await ingest_file(p, f"vault:{p.stem}")
            if n:
                sources_indexed.append(p.name)
                total_chunks += n

    logger.info(
        "RAG ingest complete: %d chunks from %d files",
        total_chunks,
        len(sources_indexed),
    )
    return {"indexed_chunks": total_chunks, "sources": sources_indexed}


async def retrieve(query: str, k: int = TOP_K) -> list[dict]:
    """
    Retrieve top-k relevant chunks for a query string.
    Returns list of {"text": str, "source": str}.
    Returns [] if RAG is unavailable, index is empty, or no matches pass MIN_SCORE.
    """
    _, collection = _get_client()
    if collection is None:
        return []

    query_embedding = await _embed([query])
    if query_embedding is None:
        return []

    try:
        count = collection.count()
        if count == 0:
            return []

        results = collection.query(
            query_embeddings=query_embedding,
            n_results=min(k, count),
            include=["documents", "metadatas", "distances"],
        )

        chunks: list[dict] = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # ChromaDB cosine distance ∈ [0, 2]; convert to similarity ∈ [0, 1]
            similarity = 1.0 - (dist / 2.0)
            if similarity >= MIN_SCORE:
                chunks.append({"text": doc, "source": meta.get("source", "unknown")})
        return chunks

    except Exception as exc:
        logger.warning("RAG retrieval failed: %s", exc)
        return []


async def status() -> dict:
    """Return RAG status dict — safe to call from any endpoint."""
    if not _CHROMA_AVAILABLE:
        return {"available": False, "indexed_chunks": 0, "collection": COLLECTION_NAME,
                "reason": "chromadb not installed"}
    _, collection = _get_client()
    if collection is None:
        return {"available": False, "indexed_chunks": 0, "collection": COLLECTION_NAME}
    try:
        count = collection.count()
        return {"available": True, "indexed_chunks": count, "collection": COLLECTION_NAME}
    except Exception:
        return {"available": False, "indexed_chunks": 0, "collection": COLLECTION_NAME}
