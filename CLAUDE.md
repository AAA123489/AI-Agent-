# CLAUDE.md —— AI 工作流 Agent 引擎

> 让 Claude 在新对话中快速恢复上下文，接着当前进度继续开发。

---

## 项目定位

**不依赖 LangChain/CrewAI，基于 Anthropic SDK 裸写 Agent Loop，理解每一步原理。**

跟项目一（RAG 知识库问答）互补：项目一把 RAG 做成工具，项目二让 Agent 自主规划、调度、组合多个工具。

- 仓库：`https://github.com/AAA123489/AI-Agent-`
- 本地路径：`e:\vscode-program\AI 工作流 Agent —— 自然语言驱动的多工具编排系统\`
- Python 虚拟环境：`.venv`（已装好全部依赖）
- 项目一（RAG 知识库）：`e:\vscode-program\AI_Agent_Project\`

---

## 开发进度

### ✅ 已完成

| 事项 | 说明 |
|------|------|
| 环境搭建 | `.venv`、所有 pip 依赖、`.env`（API Key 已配）、`.gitignore` |
| Git 仓库 | 独立仓库，已推 GitHub |
| 目录结构 | `main.py`、`agent_loop.py`、`config.py`、`prompts.py`、`tools/`、`tests/`、`static/` |
| `agent_loop.py` | **Anthropic SDK 原生 tool use**，核心循环完整 |
| `tools/get_time.py` | 第 1 天假工具，验证循环能跑 |
| `main.py` | `GET /health` + `POST /agent` |
| `config.py` | 从 `.env` 加载配置，提供全局 `config` 对象 |
| `prompts.py` | 系统 Prompt 模板 |

### 🔲 待完成

| 天数 | 任务 | 状态 |
|------|------|------|
| 第 1 天 | **验证 Agent Loop 能跑通**（curl 测试） | ✅ |
| 第 2 天 | 正式对接 Claude API tool use（已切换为 OpenAI SDK + DeepSeek） | ✅ |
| 第 3 天 | 接入项目一 RAG 知识库 | 🔲 |
| 第 4 天 | 更多工具（Web Search + File + Code）+ 容错 + Rich 输出 | 🔲 |
| 第 5 天 | 前端 SSE 流式 + Agent 思考可视化 | 🔲 |
| 第 6 天 | pytest + README + 前端打磨 | 🔲 |
| 第 7 天 | 演示视频 + 简历描述 + 面试准备 | 🔲 |

---

## 技术决策（重要！）

### 1. 为什么选 Anthropic SDK 而不是 OpenAI SDK
- Anthropic 的 tool use 流程更底层：`content` 是混合列表（text + tool_use 块），需要手动遍历解析
- 参数 `input` 已经是 dict，不用 `json.loads()`
- system prompt 独立传参，不混入 messages
- 面试能解释每一步："LLM 为什么选这个工具、结果怎么注入上下文"

### 2. 为什么 model 不硬编码
- `agent_loop.py` 默认值走 `config.MODEL`
- 所有配置统一在 `config.py` → `.env`，一处改全局生效

### 3. tools 数据结构
```python
tools = {
    "get_current_time": {
        "handler": async_function,  # 可调用的异步函数
        "schema": {                 # Anthropic SDK tool use schema
            "name": "get_current_time",
            "description": "返回当前的日期和时间",
            "input_schema": {"type": "object", "properties": {}, "required": []}
        }
    }
}
```

---

## 文件用途速览

| 文件 | 做什么 | 当前状态 |
|------|--------|----------|
| `main.py` | FastAPI 入口，`/health` + `POST /agent` | 第 1 天完成 |
| `agent_loop.py` | Agent 核心循环，Anthropic SDK 原生 tool use | 第 1 天完成 |
| `config.py` | 读 `.env`，提供全局 `config` 对象 | 完成 |
| `prompts.py` | 系统 Prompt 模板 `SYSTEM_PROMPT` | 初版可用 |
| `tools/get_time.py` | 第 1 天假工具 `get_current_time` | 完成 |
| `tools/__init__.py` | 工具模块入口 | 空 |
| `tests/__init__.py` | 测试模块入口 | 空 |
| `.env` | API Key + 配置（Git 忽略） | 已配 |
| `.env.example` | 配置模板（提交 Git） | 完成 |
| `.gitignore` | 忽略 .venv、.env、__pycache__ 等 | 完成 |

---

## Agent Loop 核心流程

```
用户输入 → POST /agent
  ↓
messages = [{"role": "user", "content": user_input}]
  ↓
for step in range(max_iterations):
    response = client.messages.create(
        system=system_prompt,
        messages=messages,
        tools=tools_schema
    )
    ↓
    if stop_reason == "end_turn":
        return 提取文本  →  任务完成
    ↓
    if stop_reason == "tool_use":
        messages.append({"role": "assistant", "content": response.content})
        for block in response.content:
            if block.type == "tool_use":
                output = await tools[block.name]["handler"](**block.input)
        messages.append({"role": "user", "content": [tool_result_blocks]})
        → 继续循环
```

---

## 下一步做什么

1. **立即**：跑 `python main.py`，curl 测试 `POST /agent`，确认 Agent Loop 能正确调 `get_current_time`
2. **第 2 天**（其实已经提前完成）—— Anthropic SDK 原生 tool use 已经写好了
3. **第 3 天**：写 `tools/rag_search.py`，对接项目一的 Chroma 向量库
4. **第 4 天**：`tools/web_search.py`、`tools/file_tools.py`、容错、Rich 终端输出
5. **第 5 天**：SSE 流式改造、`static/agent.html` 前端
6. **第 6 天**：pytest 测试、README
7. **第 7 天**：演示视频、简历描述

---

## 关键代码片段

### 添加新工具的标准方式
```python
# 1. 写工具文件 tools/xxx.py
async def my_tool(param: str) -> str:
    return f"结果: {param}"

TOOL_SCHEMA = {
    "name": "my_tool",
    "description": "工具描述",
    "input_schema": {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "参数说明"}
        },
        "required": ["param"]
    }
}

# 2. 在 main.py 里注册
from tools.xxx import my_tool, TOOL_SCHEMA
tools["my_tool"] = {"handler": my_tool, "schema": TOOL_SCHEMA}
```

### 配置文件 `.env`
```
ANTHROPIC_API_KEY=sk-ant-...      # 必填
MODEL=claude-sonnet-5-20251201    # 可选，默认值
MAX_TOKENS=4096                   # 可选
MAX_ITERATIONS=10                 # 可选
```
