import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import session_store
from tool.todo import todo


class SessionTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = self.enterContext(TemporaryDirectory())
        database = Path(directory) / "sessions.sqlite3"
        self.enterContext(patch.object(session_store, "DB_PATH", database))
        session_store.init_db()

    def test_history_can_be_restored_by_session_id(self) -> None:
        history = [
            {"role": "user", "content": "What is 7 × 8?"},
            {"role": "assistant", "content": "56"},
        ]
        other_history = [{"role": "user", "content": "A separate conversation"}]
        session_store.save_messages("1", history)
        session_store.save_messages("default", other_history)

        # Store operations close their connections. Run startup again before loading.
        session_store.init_db()

        self.assertEqual(session_store.load_messages("1"), history)
        self.assertEqual(session_store.load_messages("default"), other_history)

    def test_todos_are_visible_only_in_their_own_session(self) -> None:
        added = json.loads(todo("1", action="add", title="Submit the exam"))

        self.assertEqual(added["title"], "Submit the exam")
        self.assertEqual(json.loads(todo("1", action="list")), [added])
        self.assertEqual(json.loads(todo("default", action="list")), [])
