"""计算器工具的参数说明与本地实现。"""


CALCULATOR_SCHEMA = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "将两个数字相乘并返回乘积。",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "第一个乘数"},
                "b": {"type": "number", "description": "第二个乘数"},
            },
            "required": ["a", "b"],
            "additionalProperties": False,
        },
    },
}


def calculator(a: int | float, b: int | float) -> int | float:
    if type(a) not in (int, float) or type(b) not in (int, float):
        raise ValueError("a 和 b 必须是数字。")
    try:
        return a * b
    except OverflowError as exc:
        raise ValueError("数字超出计算范围。") from exc
