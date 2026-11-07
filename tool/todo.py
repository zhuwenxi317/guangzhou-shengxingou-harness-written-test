"""添加和查看当前会话的待办。"""

import json
from contextlib import closing

from session_store import connect_db


TODO_SCHEMA = {
    "type": "function",
    "function": {
        "name": "todo",
        "description": "添加或查看当前会话中的待办事项。",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["add", "list"]},
                "title": {"type": "string", "description": "待办内容，仅在 add 时提供。"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    },
}


def todo(session_id: str, /, action: str, title: str | None = None) -> str:
    if action == "list":
        if title is not None:
            raise ValueError("查看待办时不需要 title。")
        with closing(connect_db()) as db:
            rows = db.execute(
                "SELECT todo_id, title FROM todos WHERE session_id = ? ORDER BY todo_id",
                (session_id,),
            ).fetchall()
        return json.dumps([{"todo_id": todo_id, "title": text} for todo_id, text in rows], ensure_ascii=False)

    if action != "add":
        raise ValueError("action 必须是 add 或 list。")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("添加待办时需要非空的 title。")

    title = title.strip()
    with closing(connect_db()) as db, db:
        # 首轮工具调用可能早于聊天历史写入，先保证外键所指的会话存在。
        db.execute("""
            INSERT INTO sessions (session_id, messages_json) VALUES (?, '[]')
            ON CONFLICT(session_id) DO NOTHING
        """, (session_id,))
        cursor = db.execute(
            "INSERT INTO todos (session_id, title) VALUES (?, ?)",
            (session_id, title),
        )
    return json.dumps({"todo_id": cursor.lastrowid, "title": title}, ensure_ascii=False)
