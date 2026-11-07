"""最小多轮助手：在当前进程内保存对话历史。"""

import json
import os
import sqlite3
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from agent.assistant import ASSISTANT
from session_store import init_db, load_messages, save_messages
from tool.registry import TOOLS


MAX_MODEL_CALLS = 5
AGENT_TOOLS = {name: TOOLS[name] for name in ASSISTANT["tools"]}


def call_llm(messages: list[dict]) -> dict:
    """发送对话和工具说明，返回模型的完整消息。"""
    api_key = os.getenv("LLM_API_KEY", "").strip()
    base_url = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
    model = os.getenv("LLM_MODEL", "").strip()
    if not all((api_key, base_url, model)):
        raise ValueError("请先在 .env 中填写 LLM_API_KEY、LLM_BASE_URL 和 LLM_MODEL。")

    request = Request(
        url=f"{base_url}/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": messages,
            "tools": [schema for schema, _ in AGENT_TOOLS.values()],
        }).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        result = json.load(response)

    message = result["choices"][0]["message"]
    if not isinstance(message, dict):
        raise ValueError("模型没有返回有效的消息。")
    return message


def execute_tool(tool_call: dict) -> str:
    """按模型给出的工具名查找函数，并传入解析后的参数。"""
    function = tool_call["function"]
    registered_tool = AGENT_TOOLS.get(function["name"])
    if registered_tool is None:
        return "错误：未知工具。"
    _, handler = registered_tool

    try:
        arguments = json.loads(function["arguments"])
    except (json.JSONDecodeError, TypeError):
        return "错误：工具参数必须是有效的 JSON 对象。"

    if not isinstance(arguments, dict):
        return "错误：工具参数必须是 JSON 对象。"

    try:
        return str(handler(**arguments))
    except TypeError:
        return "错误：工具参数与函数签名不匹配。"
    except ValueError as exc:
        return f"错误：{exc}"


def run_agent(user_input: str, messages: list[dict]) -> str:
    # 本轮的用户消息、工具调用和工具结果先放在临时列表里。
    turn = [{"role": "user", "content": user_input}]

    for _ in range(MAX_MODEL_CALLS):
        message = call_llm([*messages, *turn])
        tool_calls = message.get("tool_calls")
        content = message.get("content")

        if not tool_calls:
            if not isinstance(content, str) or not content.strip():
                raise ValueError("模型没有返回有效的文本回复。")
            turn.append({"role": "assistant", "content": content})
            messages.extend(turn)
            return content

        turn.append({
            "role": "assistant",
            "content": content,
            "tool_calls": tool_calls,
        })
        for tool_call in tool_calls:
            turn.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": execute_tool(tool_call),
            })

    raise ValueError("已达到本轮的模型调用上限，未获得最终回答。")


def main() -> int:
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
    try:
        init_db()
    except sqlite3.Error as exc:
        print(f"无法初始化会话数据库：{exc}", file=sys.stderr)
        return 1

    session_id = "default"
    print("输入 /session <ID> 切换会话，输入 exit 或 quit 退出。")
    while True:
        try:
            user_input = input(f"[{session_id}] 你：").strip()
            if user_input.lower() in {"exit", "quit"}:
                return 0
            if not user_input:
                print("请输入非空消息。", file=sys.stderr)
                continue

            parts = user_input.split(maxsplit=1)
            if parts[0] == "/session":
                if len(parts) == 1 or any(char.isspace() for char in parts[1]):
                    print("用法：/session <ID>，ID 中不能有空格。", file=sys.stderr)
                    continue
                session_id = parts[1]
                continue

            messages = load_messages(session_id)
            system_message = {"role": "system", "content": ASSISTANT["system_prompt"]}
            if messages and messages[0]["role"] == "system":
                messages[0] = system_message
            else:
                messages = [system_message, *(messages or [])]
            message = run_agent(user_input, messages)
            save_messages(session_id, messages)
            print(f"助手：{message}")
        except sqlite3.Error as exc:
            print(f"无法读取或保存会话历史：{exc}", file=sys.stderr)
        except HTTPError as exc:
            print(f"模型请求失败，HTTP 状态码：{exc.code}。请检查接口、密钥和模型配置。", file=sys.stderr)
        except URLError:
            print("无法连接模型服务，请检查网络和 LLM_BASE_URL。", file=sys.stderr)
        except (TimeoutError, OSError):
            print("模型请求超时或发生网络错误。", file=sys.stderr)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            print("模型服务返回的数据格式不符合预期。", file=sys.stderr)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。", file=sys.stderr)
            return 0


if __name__ == "__main__":
    sys.exit(main())
