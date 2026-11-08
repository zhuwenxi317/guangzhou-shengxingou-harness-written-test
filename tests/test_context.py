import unittest
from copy import deepcopy
from unittest.mock import patch

import server
from context_manager import CONTEXT_MAX_CHARS, build_context, compression_cutoff


def calculator_turn(call_id: str) -> list[dict]:
    return [
        {"role": "user", "content": "What is 7 × 8?"},
        {"role": "assistant", "content": None, "tool_calls": [{
            "id": call_id,
            "type": "function",
            "function": {"name": "calculator", "arguments": '{"a": 7, "b": 8}'},
        }]},
        {"role": "tool", "tool_call_id": call_id, "content": "56"},
        {"role": "assistant", "content": "56"},
    ]


class ContextTests(unittest.TestCase):
    def test_keeps_five_complete_turns_without_mutating_history(self) -> None:
        system = {"role": "system", "content": "Test assistant"}
        oldest = calculator_turn("discarded-call")
        retained = calculator_turn("retained-call")
        for number in range(3, 7):
            retained.extend([
                {"role": "user", "content": f"Question {number}"},
                {"role": "assistant", "content": f"Answer {number}"},
            ])
        history = [system, *oldest, *retained]
        original_history = deepcopy(history)
        current_turn = [{"role": "user", "content": "Current question"}]

        self.assertEqual(compression_cutoff(history, current_turn, "", 0), 0)
        self.assertEqual(build_context(history, current_turn), [*history, *current_turn])

        oldest[0]["content"] = "x" * CONTEXT_MAX_CHARS
        history = [system, *oldest, *retained]
        original_history = deepcopy(history)
        cutoff = compression_cutoff(history, current_turn, "", 0)
        context = build_context(history, current_turn, covered=cutoff)

        self.assertEqual(cutoff, len(oldest))
        self.assertEqual(context, [system, *retained, *current_turn])
        self.assertEqual(history, original_history)

    def test_summary_is_reused_until_length_exceeds_threshold(self) -> None:
        oldest = calculator_turn("old-call")
        oldest[0]["content"] = "x" * CONTEXT_MAX_CHARS
        recent = calculator_turn("recent-call")
        history = [*oldest, *recent]
        current = [{"role": "user", "content": "What was the result?"}]

        with patch.object(server, "load_summary", side_effect=[("", 0), ("Result was 56.", 4)]), \
                patch.object(server, "save_summary") as save, \
                patch.object(server, "call_llm", return_value={"content": "Result was 56."}) as model:
            summary, covered = server.refresh_summary(history, current, "test")
            self.assertEqual((summary, covered), ("Result was 56.", len(oldest)))
            self.assertEqual(server.refresh_summary(history, current, "test"), (summary, covered))

        model.assert_called_once()
        self.assertFalse(model.call_args.kwargs["use_tools"])
        save.assert_called_once_with("test", summary, covered)
        self.assertIn(summary, build_context(history, current, summary, covered)[0]["content"])
