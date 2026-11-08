"""在操作完成时单独提交 SQLite 日志。"""

import logging
import sqlite3
from contextlib import closing, contextmanager
from time import perf_counter

from session_store import connect_db


@contextmanager
def trace_event(
    session_id: str, trace_id: str | None, step: int, event: str, name: str,
    *, tool_call_id: str | None = None, message_count: int | None = None,
):
    outcome: dict[str, str | None] = {"error": None}
    start = perf_counter()
    try:
        yield outcome
    except BaseException as exc:
        outcome["error"] = type(exc).__name__
        raise
    finally:
        if trace_id is not None:
            duration_ms = (perf_counter() - start) * 1000
            try:
                with closing(connect_db()) as db, db:
                    db.execute("""
                        INSERT INTO runtime_events (
                            session_id, trace_id, step, event, name, tool_call_id,
                            message_count, duration_ms, error
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (session_id, trace_id, step, event, name, tool_call_id,
                          message_count, duration_ms, outcome["error"]))
            except sqlite3.Error:
                logging.warning("无法保存 Runtime 日志。")
