"""从完整历史中选择本次模型请求需要的消息。"""

HISTORY_TURNS = 5


def build_context(history: list[dict], turn: list[dict]) -> list[dict]:
    system_messages = history[:1] if history and history[0]["role"] == "system" else []
    # 每条 user 消息标记一轮的起点，后面的工具消息随整轮保留。
    turn_starts = [index for index, message in enumerate(history) if message["role"] == "user"]
    recent_history = []
    if turn_starts:
        start = turn_starts[max(0, len(turn_starts) - HISTORY_TURNS)]
        recent_history = history[start:]
    return [*system_messages, *recent_history, *turn]
