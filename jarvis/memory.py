"""Persistent memory + user profile for Jarvis.

Stores facts the LLM learns about each user (preferences, routines,
context) and full conversation history. Both are injected into every
LLM call so the assistant "knows" the user across restarts.
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DB_PATH = str(Path(__file__).resolve().parent / "data" / "memory.db")
ET = ZoneInfo("America/New_York")

SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',  -- preference, routine, context, general
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_facts_user ON facts(user_id);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,                        -- user, assistant, tool, system
    content TEXT,
    tool_calls TEXT,                           -- JSON
    tool_call_id TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id, id);
"""


def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with _conn() as c:
        c.executescript(SCHEMA)


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ---- Facts ----

def add_fact(user_id: str, content: str, category: str = "general") -> int:
    """Store a new fact about the user. Returns fact id."""
    with _conn() as c:
        cursor = c.execute(
            "INSERT INTO facts (user_id, category, content) VALUES (?, ?, ?)",
            (user_id, category, content.strip()),
        )
        return cursor.lastrowid


def list_facts(user_id: str) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, category, content, updated_at FROM facts WHERE user_id = ? ORDER BY category, id",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def delete_fact(user_id: str, fact_id: int) -> bool:
    with _conn() as c:
        cursor = c.execute(
            "DELETE FROM facts WHERE id = ? AND user_id = ?",
            (fact_id, user_id),
        )
        return cursor.rowcount > 0


def delete_fact_by_content(user_id: str, content_substr: str) -> int:
    """Delete facts matching a substring. Returns rows deleted."""
    with _conn() as c:
        cursor = c.execute(
            "DELETE FROM facts WHERE user_id = ? AND LOWER(content) LIKE ?",
            (user_id, f"%{content_substr.lower()}%"),
        )
        return cursor.rowcount


def facts_as_prompt_block(user_id: str) -> str:
    """Render facts as a block to inject into the system prompt."""
    facts = list_facts(user_id)
    if not facts:
        return ""
    lines = ["What you know about the user (from past conversations):"]
    by_cat = {}
    for f in facts:
        by_cat.setdefault(f["category"], []).append(f)
    for cat in sorted(by_cat.keys()):
        lines.append(f"  [{cat}]")
        for f in by_cat[cat]:
            lines.append(f"    - {f['content']} (#{f['id']})")
    return "\n".join(lines)


# ---- Messages / conversation history ----

def log_message(user_id: str, role: str, content: Optional[str] = None,
                tool_calls: Optional[list] = None,
                tool_call_id: Optional[str] = None) -> None:
    """Persist a message to the conversation log."""
    with _conn() as c:
        c.execute(
            "INSERT INTO messages (user_id, role, content, tool_calls, tool_call_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                user_id, role, content,
                json.dumps(tool_calls) if tool_calls else None,
                tool_call_id,
            ),
        )


def recent_messages(user_id: str, limit: int = 20) -> list[dict]:
    """Load recent messages in chronological order, OpenAI format."""
    with _conn() as c:
        rows = c.execute(
            "SELECT role, content, tool_calls, tool_call_id FROM messages "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()

    result = []
    for r in reversed(rows):  # chronological
        msg = {"role": r["role"]}
        if r["content"] is not None:
            msg["content"] = r["content"]
        if r["tool_calls"]:
            try:
                msg["tool_calls"] = json.loads(r["tool_calls"])
            except json.JSONDecodeError:
                pass
        if r["tool_call_id"]:
            msg["tool_call_id"] = r["tool_call_id"]
        # assistant messages with tool_calls need a string content
        if msg["role"] == "assistant" and "content" not in msg:
            msg["content"] = ""
        result.append(msg)
    return result


def clear_history(user_id: str) -> int:
    with _conn() as c:
        cursor = c.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
        return cursor.rowcount


def trim_history(user_id: str, keep_last: int = 40) -> None:
    """Keep only the most recent `keep_last` messages for a user."""
    with _conn() as c:
        c.execute(
            """DELETE FROM messages WHERE user_id = ? AND id NOT IN (
                SELECT id FROM messages WHERE user_id = ?
                ORDER BY id DESC LIMIT ?
            )""",
            (user_id, user_id, keep_last),
        )
