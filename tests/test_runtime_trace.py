import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import server
import session_store


class RuntimeTraceTests(unittest.TestCase):
    def test_completed_events_survive_failed_followup_request(self) -> None:
        directory = self.enterContext(TemporaryDirectory())
        self.enterContext(patch.object(session_store, "DB_PATH", Path(directory) / "trace.sqlite3"))
        session_store.init_db()

        def tool_call(call_id: str, arguments: str) -> dict:
            return {"id": call_id, "function": {"name": "calculator", "arguments": arguments}}

        calls = [tool_call("ok", '{"a": 2, "b": 3}'), tool_call("bad", "{}")]
        history = []
        with patch.object(server, "call_llm", side_effect=[{"tool_calls": calls}, TimeoutError()]):
            with self.assertRaises(TimeoutError):
                server.run_agent("Calculate", history, "window-1", trace_id="test-turn")

        self.assertEqual(history, [])
        with closing(session_store.connect_db()) as db:
            rows = db.execute("""
                SELECT step, event, name, tool_call_id, message_count, error
                FROM runtime_events WHERE session_id = ? AND trace_id = ? ORDER BY event_id
            """, ("window-1", "test-turn")).fetchall()
        self.assertEqual(rows, [
            (1, "llm_post", "answer", None, 1, None),
            (1, "tool_call", "calculator", "ok", None, None),
            (1, "tool_call", "calculator", "bad", None, "invalid_arguments"),
            (2, "llm_post", "answer", None, 4, "TimeoutError"),
        ])
