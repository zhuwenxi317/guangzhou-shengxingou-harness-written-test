# 最小 Agent：本地会话与工具调用

当前实现多轮文本对话：用户输入 → 携带历史 messages 请求模型 → 提取 message.content → 保存本轮问答 → 等待下一次输入。
输入 `exit`、`quit` 或按 Ctrl+C 退出。成功完成的问答和工具消息保存到项目目录下的 `sessions.sqlite3`，该文件已被 Git 忽略。
输入 `/session <ID>` 切换会话，例如 `/session window-1`。重启后切回相同 ID，下一次提问时会从数据库加载它的历史。默认 ID 是 `default`。
每个会话有独立的历史，支持计算器工具调用。当前尚未实现上下文压缩，长对话仍可能超过模型的上下文限制。请用单个 CLI 进程操作数据库，同一个 ID 的并发写入可能覆盖历史。

## 运行

在 PowerShell 中执行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe server.py
```

首次运行前编辑本地 `.env`：

- `LLM_API_KEY`：你的 API 密钥。
- `LLM_BASE_URL`：服务商提供的 OpenAI 兼容接口基础地址，通常以 `/v1` 结尾；不要包含 `/chat/completions`。
- `LLM_MODEL`：服务商提供的模型 ID。

程序会向 `LLM_BASE_URL/chat/completions` 发送请求，使用系统消息、历史问答与本次用户消息，不开启流式输出。
`.env` 和 `.venv` 已加入 Git 忽略规则；提交 `.env.example` 说明配置项。不要提交密钥。

## 代码入口

- `main()`：加载环境配置，循环接收输入，按当前 ID 加载历史并在回答成功后保存。
- `session_store.py`：SQLite 存储模块，以会话 ID 为主键，每个会话保存一份 JSON 消息列表。
- `run_agent()`：携带当前会话历史请求模型，执行工具，获得最终回复后保存整轮消息。
- `call_llm()`：向模型发送消息和工具 Schema，返回完整的 assistant 消息。

## 开发记录

1. 用户要求：先搭建最简单的单轮调用，提取模型 message 作为输出，使用 `.env` 配置密钥，并用 Git 记录每个开发阶段。
2. 实现选择：入口暂时集中在 `server.py`，使用标准库 HTTP 客户端与 python-dotenv；等加入工具时再拆分 Runtime 与 Agent 配置。
3. 验证边界：终端环境启动故障，尚未完成模拟接口测试与真实模型调用验证。
4. 用户要求增加连续提问与进程内上下文：历史按 user / assistant 角色放入 messages，每轮重发，退出即清空。终端环境启动故障使本次自动验证与 Git 提交暂未完成。
5. 用户要求跨进程恢复会话：将会话历史移至 SQLite，沿用 `/session <ID>` 选择历史。
6. 将计算器加入 `tool/registry.py`。模型请求从注册表读取 Schema，执行时按工具名查找 Python 函数。
7. 在 `agent/assistant.py` 集中定义系统提示词和工具名单。发送 Schema 和执行工具都受该名单约束，技能列表暂为空。
