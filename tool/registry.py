"""工具名对应模型可见的 Schema 和本地执行函数。"""

from tool.calculator import CALCULATOR_SCHEMA, calculator


TOOLS = {
    CALCULATOR_SCHEMA["function"]["name"]: (CALCULATOR_SCHEMA, calculator),
}
