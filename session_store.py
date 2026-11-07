"""按 session_id 读取和保存会话历史。"""

import json
import sqlite3
from contextlib import closing
from pathlib import Path


DB_PATH = Path(__file__).resolve().with_name("sessions.sqlite3")


def init_db() -> None:
    with closing(sqlite3.connect(DB_PATH)) as db, db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY NOT NULL,
                messages_json TEXT NOT NULL
            )
        """)


def load_messages(session_id: str) -> list[dict] | None:
    with closing(sqlite3.connect(DB_PATH)) as db:
        row = db.execute(
            "SELECT messages_json FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    if row is None:
        return None
    return json.loads(row[0])


def save_messages(session_id: str, messages: list[dict]) -> None:
    messages_json = json.dumps(messages, ensure_ascii=False)
    with closing(sqlite3.connect(DB_PATH)) as db, db:
        db.execute("""
            INSERT INTO sessions (session_id, messages_json) VALUES (?, ?)
            ON CONFLICT(session_id) DO UPDATE SET messages_json = excluded.messages_json
        """, (session_id, messages_json))
