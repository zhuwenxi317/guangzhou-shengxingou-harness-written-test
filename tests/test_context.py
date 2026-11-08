import unittest
from copy import deepcopy

from context_manager import build_context


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

        context = build_context(history, current_turn)

        self.assertEqual(context, [system, *retained, *current_turn])
        self.assertEqual(history, original_history)
