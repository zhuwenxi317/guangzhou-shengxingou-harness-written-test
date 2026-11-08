"""工具名对应模型可见的 Schema 和本地执行函数。"""

from tool.calculator import CALCULATOR_SCHEMA, calculator
from tool.search import SEARCH_SCHEMA, search
from tool.todo import TODO_SCHEMA, todo


def run_calculator(_session_id: str, /, a: int | float, b: int | float) -> int | float:
    return calculator(a, b)


TOOLS = {
    CALCULATOR_SCHEMA["function"]["name"]: (CALCULATOR_SCHEMA, run_calculator),
    TODO_SCHEMA["function"]["name"]: (TODO_SCHEMA, todo),
    SEARCH_SCHEMA["function"]["name"]: (SEARCH_SCHEMA, search),
}
