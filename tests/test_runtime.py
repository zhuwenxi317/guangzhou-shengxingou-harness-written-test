import json
import unittest
from unittest.mock import patch

import server


def calculator_call(call_id: str) -> dict:
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": "calculator",
            "arguments": json.dumps({"a": 128, "b": 36}),
        },
    }


class RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.history = [{"role": "system", "content": "Test assistant"}]

    def test_direct_answer_calls_model_once(self) -> None:
        with patch.object(server, "call_llm", return_value={"content": "Hello"}) as model:
            answer = server.run_agent("Hi", self.history, "test")

        model.assert_called_once_with([
            self.history[0],
            {"role": "user", "content": "Hi"},
        ])
        self.assertEqual(answer, "Hello")
        self.assertEqual(self.history[1:], [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
        ])

    def test_tool_result_is_returned_to_model_with_matching_id(self) -> None:
        tool_call = calculator_call("calc-1")
        with patch.object(server, "call_llm", side_effect=[
            {"content": None, "tool_calls": [tool_call]},
            {"content": "The result is 4608."},
        ]) as model:
            answer = server.run_agent("Calculate 128 × 36", self.history, "test")

        self.assertEqual(answer, "The result is 4608.")
        self.assertEqual(model.call_count, 2)
        second_request = model.call_args.args[0]
        self.assertEqual(second_request[-2]["tool_calls"], [tool_call])
        self.assertEqual(second_request[-1], {
            "role": "tool", "tool_call_id": "calc-1", "content": "4608",
        })
        self.assertEqual(self.history[:-1], second_request)

    def test_model_call_limit_leaves_history_intact(self) -> None:
        previous_history = self.history.copy()
        replies = [{"tool_calls": [calculator_call(f"calc-{i}")]} for i in range(5)]
        with patch.object(server, "call_llm", side_effect=replies) as model:
            with self.assertRaisesRegex(ValueError, "模型调用上限"):
                server.run_agent("Keep calculating", self.history, "test")

        self.assertEqual(model.call_count, 5)
        self.assertEqual(self.history, previous_history)
