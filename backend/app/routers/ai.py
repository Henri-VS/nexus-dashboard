import json
import uuid
from datetime import datetime
from typing import AsyncIterator

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, delete, select

from app.core.config import settings
from app.core.database import engine, get_session
from app.core import rag
from app.models.ai import Conversation, Message

router = APIRouter()


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{settings.ollama_host}/api/tags")
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                embed_ready = any("nomic-embed-text" in m for m in models)
                return {
                    "status": "online",
                    "model": settings.ollama_default_model,
                    "rag_embed_model": "nomic-embed-text",
                    "rag_ready": embed_ready,
                }
    except Exception:
        pass
    return {
        "status": "offline",
        "model": settings.ollama_default_model,
        "rag_ready": False,
    }


# ── Models ────────────────────────────────────────────────────────────────────

@router.get("/models")
async def list_models():
    """Return models available in Ollama. 503 if Ollama is unreachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_host}/api/tags")
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama unreachable at {settings.ollama_host}",
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama error: {exc.response.status_code}",
        )


# ── Conversations ─────────────────────────────────────────────────────────────

@router.get("/conversations")
async def list_conversations(session: Session = Depends(get_session)):
    """Return all conversations ordered newest first."""
    convs = session.exec(
        select(Conversation).order_by(Conversation.updated_at.desc())  # type: ignore[arg-type]
    ).all()
    return convs


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    session: Session = Depends(get_session),
):
    """Delete a conversation and all its messages."""
    conv = session.exec(
        select(Conversation).where(Conversation.conversation_id == conversation_id)
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    session.exec(delete(Message).where(Message.conversation_id == conversation_id))  # type: ignore[arg-type]
    session.delete(conv)
    session.commit()


# ── History / per-conversation messages ──────────────────────────────────────

def _get_conversation_messages(conversation_id: str, session: Session):
    """Shared logic for both /history/<id> and /conversations/<id>."""
    conv = session.exec(
        select(Conversation).where(Conversation.conversation_id == conversation_id)
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = session.exec(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp)  # type: ignore[arg-type]
    ).all()
    return {"conversation": conv, "messages": messages}


@router.get("/history/{conversation_id}")
async def get_history(
    conversation_id: str,
    session: Session = Depends(get_session),
):
    """Return all messages for a conversation (legacy path)."""
    return _get_conversation_messages(conversation_id, session)


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    session: Session = Depends(get_session),
):
    """Return all messages for a conversation."""
    return _get_conversation_messages(conversation_id, session)


# ── SSE stream ────────────────────────────────────────────────────────────────

async def _stream_and_persist(
    model: str,
    ollama_messages: list[dict],
    conv_id: str,
    rag_sources: list[str] | None = None,
) -> AsyncIterator[str]:
    """
    Proxy Ollama /api/chat as SSE, then persist the full assistant reply.

    SSE events emitted:
      data: {"content": "<token>"}        — streaming chunk
      data: {"done": true, "conversation_id": "...", "model": "..."}
      data: {"error": "<message>"}        — on failure

    NOTE: This generator outlives the FastAPI Depends session, so it opens
    its own SQLite session for the final persist step.
    """
    accumulated: list[str] = []
    error_occurred = False

    payload = {
        "model": model,
        "messages": ollama_messages,
        "stream": True,
    }

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{settings.ollama_host}/api/chat",
                json=payload,
            ) as resp:

                if resp.status_code != 200:
                    body = await resp.aread()
                    detail = body.decode(errors="replace")
                    yield f"event: error\ndata: {json.dumps({'detail': detail})}\n\n"
                    error_occurred = True
                    return

                async for raw_line in resp.aiter_lines():
                    if not raw_line:
                        continue

                    try:
                        chunk = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue

                    token: str = chunk.get("message", {}).get("content", "")
                    if token:
                        accumulated.append(token)
                        yield f"event: chunk\ndata: {json.dumps({'content': token})}\n\n"

                    if chunk.get("done"):
                        break

    except httpx.ConnectError:
        detail = f"Ollama unreachable at {settings.ollama_host}"
        yield f"event: error\ndata: {json.dumps({'detail': detail})}\n\n"
        error_occurred = True

    except Exception as exc:  # noqa: BLE001
        yield f"event: error\ndata: {json.dumps({'detail': str(exc)})}\n\n"
        error_occurred = True

    # Persist assistant reply — fresh session, Depends session is closed by now.
    if not error_occurred and accumulated:
        full_response = "".join(accumulated)
        with Session(engine) as db:
            db.add(Message(
                conversation_id=conv_id,
                role="assistant",
                content=full_response,
            ))
            conv = db.exec(
                select(Conversation).where(Conversation.conversation_id == conv_id)
            ).first()
            if conv:
                conv.updated_at = datetime.utcnow()
                db.add(conv)
            db.commit()

    yield f"event: done\ndata: {json.dumps({'done': True, 'conversation_id': conv_id, 'model': model, 'rag_sources': rag_sources or []})}\n\n"


# ── Chat endpoint ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT: dict = {
    "role": "system",
    "content": (
        "You are a local AI assistant running on a self-hosted homelab server via Ollama. "
        "You are integrated into Nexus, a self-hosted homelab dashboard. "
        "You have knowledge of the user's infrastructure: Docker containers, Home Assistant, "
        "Wazuh, Tailscale VPN, and Linux server administration. "
        "Be concise, technical, and direct. Never claim to be cloud-based."
    ),
}


class ChatRequest(BaseModel):
    # Single-message form (used by the frontend widget)
    message: str | None = None
    # Multi-message form (full conversation array)
    messages: list[dict] | None = None
    conversation_id: str | None = None
    model: str | None = None


@router.post("/chat")
async def chat(
    body: ChatRequest,
    model: str | None = Query(
        default=None,
        description="Ollama model. Overrides body.model. Falls back to OLLAMA_DEFAULT_MODEL.",
    ),
    session: Session = Depends(get_session),
):
    """
    Start or continue a conversation with SSE streaming.

    Accepts either:
      • {message: str, conversation_id?, model?}  ← frontend widget
      • {messages: [{role, content}], conversation_id?, model?}  ← raw API

    Model resolution: ?model= > body.model > OLLAMA_DEFAULT_MODEL env var.
    """
    if not body.message and not body.messages:
        raise HTTPException(status_code=422, detail="Provide 'message' or 'messages'")

    resolved_model = model or body.model or settings.ollama_default_model
    conv_id = body.conversation_id or str(uuid.uuid4())

    # Upsert conversation record
    conv = session.exec(
        select(Conversation).where(Conversation.conversation_id == conv_id)
    ).first()
    if conv is None:
        auto_title = (body.message or "New conversation")[:72].strip()
        if body.message and len(body.message) > 72:
            auto_title += "…"
        conv = Conversation(
            conversation_id=conv_id,
            model=resolved_model,
            title=auto_title,
        )
        session.add(conv)
    else:
        conv.model = resolved_model
        session.add(conv)

    # Extract the current user query for RAG retrieval
    if body.message:
        user_query = body.message
    elif body.messages:
        user_query = next(
            (m["content"] for m in reversed(body.messages) if m.get("role") == "user"),
            "",
        )
    else:
        user_query = ""

    # Retrieve RAG context — fails silently, never blocks chat
    rag_context: list[dict] = []
    if user_query:
        try:
            rag_context = await rag.retrieve(user_query)
        except Exception:
            rag_context = []

    # Build the messages to send to Ollama
    if body.messages:
        # Full array provided — persist each new message, use array as-is
        for msg in body.messages:
            session.add(Message(
                conversation_id=conv_id,
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
            ))
        session.commit()
        ollama_messages = body.messages
    else:
        # Single message — persist it, then load full history for context
        session.add(Message(
            conversation_id=conv_id,
            role="user",
            content=body.message,  # type: ignore[arg-type]
        ))
        session.commit()

        history = session.exec(
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.timestamp)  # type: ignore[arg-type]
        ).all()
        ollama_messages = [{"role": m.role, "content": m.content} for m in history]

    # Build system prompt, augmented with RAG context when available
    system_content = SYSTEM_PROMPT["content"]
    if rag_context:
        context_block = "\n\n".join(
            f"[Source: {c['source']}]\n{c['text']}" for c in rag_context
        )
        system_content = (
            f"{system_content}\n\n"
            f"RELEVANT CONTEXT FROM YOUR NOTES AND AUTOMATIONS:\n"
            f"{'─' * 40}\n"
            f"{context_block}\n"
            f"{'─' * 40}\n"
            f"Use the above context to answer if relevant. Cite the source name."
        )
    augmented_system = {"role": "system", "content": system_content}

    # Always inject our (possibly augmented) system message at position 0
    if not ollama_messages or ollama_messages[0].get("role") != "system":
        ollama_messages = [augmented_system] + list(ollama_messages)
    else:
        ollama_messages = [augmented_system] + list(ollama_messages[1:])

    rag_sources = [c["source"] for c in rag_context]

    return StreamingResponse(
        _stream_and_persist(resolved_model, ollama_messages, conv_id, rag_sources),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Conversation-Id": conv_id,
        },
    )
