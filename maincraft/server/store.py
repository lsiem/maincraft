"""SQLite persistence for chat sessions and messages."""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from config import DATA_DIR, PackId

DB_PATH = DATA_DIR / "chats.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Chat:
    id: str
    title: str
    pack: PackId
    created_at: str
    updated_at: str


@dataclass
class Message:
    id: str
    chat_id: str
    role: str
    content: str
    created_at: str


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT 'New Chat',
                pack TEXT NOT NULL DEFAULT 'gtnh',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
        """)


def create_chat(pack: PackId = "gtnh", title: str = "New Chat") -> Chat:
    chat_id = str(uuid.uuid4())
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO chats (id, title, pack, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (chat_id, title, pack, now, now),
        )
    return Chat(id=chat_id, title=title, pack=pack, created_at=now, updated_at=now)


def list_chats() -> list[Chat]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM chats ORDER BY updated_at DESC").fetchall()
    return [Chat(**dict(r)) for r in rows]


def get_chat(chat_id: str) -> Chat | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
    return Chat(**dict(row)) if row else None


def update_chat(chat_id: str, *, title: str | None = None, pack: PackId | None = None) -> Chat | None:
    chat = get_chat(chat_id)
    if not chat:
        return None
    new_title = title if title is not None else chat.title
    new_pack = pack if pack is not None else chat.pack
    now = _now()
    with _connect() as conn:
        conn.execute(
            "UPDATE chats SET title = ?, pack = ?, updated_at = ? WHERE id = ?",
            (new_title, new_pack, now, chat_id),
        )
    return Chat(id=chat_id, title=new_title, pack=new_pack, created_at=chat.created_at, updated_at=now)


def delete_chat(chat_id: str) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    return cur.rowcount > 0


def add_message(chat_id: str, role: str, content: str) -> Message:
    msg_id = str(uuid.uuid4())
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (id, chat_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (msg_id, chat_id, role, content, now),
        )
        conn.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now, chat_id))
    return Message(id=msg_id, chat_id=chat_id, role=role, content=content, created_at=now)


def get_messages(chat_id: str) -> list[Message]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at ASC",
            (chat_id,),
        ).fetchall()
    return [Message(**dict(r)) for r in rows]


def auto_title(chat_id: str, first_message: str) -> str:
    title = first_message.strip()[:40]
    if len(first_message.strip()) > 40:
        title += "…"
    update_chat(chat_id, title=title or "New Chat")
    return title
