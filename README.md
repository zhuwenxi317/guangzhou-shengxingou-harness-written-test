# 最小 Agent Runtime

一个用 Python 自行实现的命令行 Agent，支持工具调用、独立会话、历史摘要和 SQLite 执行日志。模型服务使用 OpenAI 兼容的 Chat Completions 接口。

## 运行

需要 Python 3.11 或更高版本，以及支持工具调用的模型。在项目根目录打开 PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

已有虚拟环境或 `.env` 时跳过对应的创建命令。编辑本地 `.env`，填写 `LLM_API_KEY`、`LLM_BASE_URL` 和 `LLM_MODEL`。基础地址使用服务商提供的地址，通常以 `/v1` 结尾，程序会自行拼接 `/chat/completions`。

```powershell
.\.venv\Scripts\python.exe server.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

单元测试使用模拟模型和临时数据库，无需 API Key。密钥文件和本地数据库已加入 Git 忽略规则。

试运行时可以先输入「搜一下项目启动命令」，再输入「把刚才的命令添加到待办」。用 `/session window-2` 切换会话，重启后用相同 ID 继续。默认会话为 `default`，输入 `exit`、`quit` 或按 Ctrl+C 退出。

## 系统设计

- `server.py` 负责 CLI、模型请求与工具循环。模型返回 `tool_calls` 时，Runtime 校验参数、执行工具，再将带有对应 `tool_call_id` 的结果交回模型。没有工具调用且有有效文本时返回最终回答。每轮回答最多请求模型五次，摘要请求单独计算。
- `tool/registry.py` 将工具名映射到参数 Schema 和本地函数。`agent/assistant.py` 指定装载名单。当前提供乘法计算器、会话待办和本地模拟搜索。待办的会话 ID 由 Runtime 注入。
- `session_store.py` 用 SQLite 保存会话历史、摘要、待办和日志。完整问答成功后写入聊天历史。待办和执行日志在各自操作完成时写入。CLI 按单进程使用设计。
- `call_llm()` 识别可选的 `reasoning_content`。调试日志只记录字段长度，推理正文不会回传模型、持久化或进入跨轮记忆。工具决策依据 `tool_calls`，用户答案取 `content`。

## Memory 召回与放置

每次提交问题时，CLI 按当前 `session_id` 从 SQLite 加载完整历史和已有摘要。召回按会话 ID 和摘要进度完成。`context_manager.py` 按以下顺序组装模型请求：

1. 系统提示词。
2. 旧历史摘要（如有），作为一条标明「仅供参考」的 assistant 消息。
3. 尚未压缩的历史原文，包括用户问题、助手回答和成对的工具调用与结果。
4. 当前轮的用户问题，以及本轮已产生的工具调用和结果。

提问时按序列化后的 JSON 字符数估算长度。超过 12,000 字符且有旧历史可压缩时，才额外请求模型合并已有摘要与新移出的完整轮次。优先保留最近五轮原文，必要时再减少原文轮数。摘要保留事实、偏好、决定、未完成事项和重要工具结果，最多保存 2,000 字符。摘要和已覆盖消息数按会话存储，后续请求可以复用。摘要失败时沿用已有摘要和未压缩历史。SQLite 保留完整原始历史。字符阈值用于触发压缩，不能保证请求符合模型的 token 上限。

## 执行日志

`runtime_events` 记录模型请求和工具执行的会话、轮次、步骤、耗时及错误类型。日志只包含元数据。以下 SQL 查询最近 20 条事件，步骤 0 代表摘要请求。

```sql
SELECT created_at, session_id, trace_id, step, event, name, tool_call_id,
       message_count, duration_ms, COALESCE(error, 'ok') AS status
FROM runtime_events ORDER BY event_id DESC LIMIT 20;
```

开发过程见 [AI Prompt 与问题解决记录](AI_DEVELOPMENT.md)。
