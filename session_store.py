"""初始化本地数据库并按 session_id 读写会话历史。"""

import json
import sqlite3
from contextlib import closing
from pathlib import Path


DB_PATH = Path(__file__).resolve().with_name("sessions.sqlite3")


def connect_db() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db() -> None:
    with closing(connect_db()) as db, db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY NOT NULL,
                messages_json TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                todo_id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES sessions(session_id),
                title TEXT NOT NULL
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS todos_by_session ON todos(session_id)")


def load_messages(session_id: str) -> list[dict] | None:
    with closing(connect_db()) as db:
        row = db.execute(
            "SELECT messages_json FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    if row is None:
        return None
    return json.loads(row[0])


def save_messages(session_id: str, messages: list[dict]) -> None:
    messages_json = json.dumps(messages, ensure_ascii=False)
    with closing(connect_db()) as db, db:
        db.execute("""
            INSERT INTO sessions (session_id, messages_json) VALUES (?, ?)
            ON CONFLICT(session_id) DO UPDATE SET messages_json = excluded.messages_json
        """, (session_id, messages_json))
