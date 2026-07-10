"""FastAPI web server for the Modpack Knowledge Engine."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.orchestrator import ModpackAgent
from agent.tools import read_player_state
from config import PACKS, PROJECT_ROOT, PackId
from server import store

logger = logging.getLogger(__name__)

app = FastAPI(title="Modpack Knowledge Engine")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_agent_lock = asyncio.Lock()
_agent = ModpackAgent("gtnh")

FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class CreateChatRequest(BaseModel):
    pack: PackId = "gtnh"
    title: str = "New Chat"


class UpdateChatRequest(BaseModel):
    title: Optional[str] = None
    pack: Optional[PackId] = None


class SendMessageRequest(BaseModel):
    content: str


class DescribeWorldRequest(BaseModel):
    description: str


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup() -> None:
    store.init_db()
    logger.info("Chat store initialized")


# ---------------------------------------------------------------------------
# Pack endpoints
# ---------------------------------------------------------------------------

@app.get("/api/packs")
def get_packs() -> list[dict[str, str]]:
    return [{"id": p.id, "name": p.display_name} for p in PACKS.values()]


# ---------------------------------------------------------------------------
# Chat CRUD
# ---------------------------------------------------------------------------

@app.get("/api/chats")
def list_chats() -> list[dict]:
    return [
        {"id": c.id, "title": c.title, "pack": c.pack, "created_at": c.created_at, "updated_at": c.updated_at}
        for c in store.list_chats()
    ]


@app.post("/api/chats", status_code=201)
def create_chat(req: CreateChatRequest) -> dict:
    chat = store.create_chat(pack=req.pack, title=req.title)
    return {"id": chat.id, "title": chat.title, "pack": chat.pack, "created_at": chat.created_at, "updated_at": chat.updated_at}


@app.get("/api/chats/{chat_id}")
def get_chat(chat_id: str) -> dict:
    chat = store.get_chat(chat_id)
    if not chat:
        raise HTTPException(404, "Chat not found")
    messages = store.get_messages(chat_id)
    return {
        "id": chat.id,
        "title": chat.title,
        "pack": chat.pack,
        "created_at": chat.created_at,
        "updated_at": chat.updated_at,
        "messages": [
            {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at}
            for m in messages
        ],
    }


@app.patch("/api/chats/{chat_id}")
def update_chat(chat_id: str, req: UpdateChatRequest) -> dict:
    chat = store.update_chat(chat_id, title=req.title, pack=req.pack)
    if not chat:
        raise HTTPException(404, "Chat not found")
    return {"id": chat.id, "title": chat.title, "pack": chat.pack, "updated_at": chat.updated_at}


@app.delete("/api/chats/{chat_id}", status_code=204)
def delete_chat(chat_id: str) -> None:
    if not store.delete_chat(chat_id):
        raise HTTPException(404, "Chat not found")


# ---------------------------------------------------------------------------
# Message streaming (SSE)
# ---------------------------------------------------------------------------

@app.post("/api/chats/{chat_id}/messages")
async def send_message(chat_id: str, req: SendMessageRequest) -> StreamingResponse:
    chat = store.get_chat(chat_id)
    if not chat:
        raise HTTPException(404, "Chat not found")

    store.add_message(chat_id, "user", req.content)

    # Auto-title on first message
    existing = store.get_messages(chat_id)
    if len(existing) == 1:
        store.auto_title(chat_id, req.content)

    history = [{"role": m.role, "content": m.content} for m in existing]

    async def event_stream():
        full = ""
        async with _agent_lock:
            _agent.set_pack(chat.pack)
            loop = asyncio.get_event_loop()

            def run_stream():
                return list(_agent.stream_with_history(history, chat.pack))

            events = await loop.run_in_executor(None, run_stream)

        for event in events:
            if event["type"] == "token":
                full += event["content"]
                yield f"data: {json.dumps(event)}\n\n"
            elif event["type"] == "tool":
                yield f"data: {json.dumps(event)}\n\n"
            elif event["type"] == "done":
                full = event.get("full", full)
                store.add_message(chat_id, "assistant", full)
                yield f"data: {json.dumps({'type': 'done', 'content': full})}\n\n"
            elif event["type"] == "error":
                yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# World state
# ---------------------------------------------------------------------------

@app.get("/api/world")
def get_world() -> dict[str, str]:
    pages = {}
    for entity in ("index", "progression", "base_infrastructure", "bottlenecks"):
        pages[entity] = read_player_state.invoke({"entity": entity})
    return pages


@app.post("/api/world/describe")
async def describe_world(req: DescribeWorldRequest) -> dict[str, str]:
    async with _agent_lock:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _agent.describe_world, req.description)
    return {"result": result}


# ---------------------------------------------------------------------------
# Static frontend (production)
# ---------------------------------------------------------------------------

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        file = FRONTEND_DIST / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(FRONTEND_DIST / "index.html")


def main() -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
