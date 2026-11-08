"""在固定的项目说明中做本地模拟搜索。"""

import json


DOCUMENTS = [
    {"title": "启动项目", "text": r"在项目目录运行 .\.venv\Scripts\python.exe server.py。"},
    {"title": "切换会话", "text": "输入 /session <ID> 切换会话。"},
    {"title": "使用待办", "text": "可以请助手添加或查看当前会话的待办。"},
]

SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search",
        "description": "按关键词搜索本地项目说明，涵盖启动、会话和待办，不查询网络。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "简短的搜索关键词，例如启动"},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}


def search(_session_id: str, /, query: str) -> str:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query 必须是非空字符串。")

    keyword = query.strip().casefold()
    matches = [
        document for document in DOCUMENTS
        if keyword in f"{document['title']} {document['text']}".casefold()
    ]
    return json.dumps(matches, ensure_ascii=False)
