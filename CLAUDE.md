# CLAUDE.md —— AI 工作流 Agent 引擎

> 让 Claude 在新对话中快速恢复上下文，接着当前进度继续开发。

---

## 项目定位

**不依赖 LangChain/CrewAI，基于 OpenAI SDK 裸写 Agent Loop，理解每一步原理。**

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
| `agent_loop.py` | **OpenAI SDK 原生 tool use**，核心循环完整（含超时+Rich） | ✅ |
| `tools/get_time.py` | 第 1 天假工具，验证循环能跑 | ✅ |
| `tools/file_tools.py` | write_file / read_file / list_files 工具（3合1） | ✅ |
| `tools/rag_search.py` | 第 3 天 RAG 知识库检索，对接项目一 Chroma 向量库 | ✅ |
| `tools/web_search.py` | 第 4 天 DuckDuckGo 免费网页搜索 | ✅ |
| `rich_display.py` | 第 4 天 Rich 终端美化（TTY 自动检测降级） | ✅ |
| `requirements.txt` | 第 4 天 项目完整依赖清单 | ✅ |
| `main.py` | `GET /health` + `POST /agent`，注册 6 个工具 | ✅ |
| `config.py` | 从 `.env` 加载配置，支持 OpenAI 兼容服务（DeepSeek 等） | ✅ |
| `prompts.py` | 系统 Prompt 模板（含 6 工具使用指引） | ✅ |

### 🔲 待完成

| 天数 | 任务 | 状态 |
|------|------|------|
| 第 1 天 | 项目骨架 + Agent Loop 最小原型 + curl 验证 | ✅ |
| 第 2 天 | 正式对接 LLM API tool use + write_file 工具 | ✅ |
| 第 3 天 | 接入项目一 RAG 知识库（rag_search） | ✅ |
| 第 4 天 | 更多工具（Web Search + File）+ 容错 + Rich 输出 | ✅ |
| 第 5 天 | 前端 SSE 流式 + Agent 思考可视化 | 🔲 |
| 第 6 天 | pytest + README + 前端打磨 | 🔲 |
| 第 7 天 | 演示视频 + 简历描述 + 面试准备 | 🔲 |

---

## 技术决策（重要！）

### 1. 为什么从 Anthropic SDK 换成了 OpenAI SDK

**原计划用 Anthropic SDK**，但用户只有 DeepSeek API Key（`sk-...` 格式），Anthropic API 不接受，返回 403。DeepSeek 兼容 OpenAI 协议。

- 切到 `openai` 包后，换 `base_url` + `key` 就能对接任意国产模型（DeepSeek、千问、智谱等）
- Agent Loop 核心思路完全不变，SDK 只是"发请求的管道"
- 面试可以讲"为什么选 OpenAI 协议而不是绑定一家厂商"

### 2. tool_choice 策略：首轮 required、后续 auto

**踩坑：DeepSeek 在 `tool_choice="auto"` 下不主动调工具**，它觉得自己"知道时间"就跳过工具直接用记忆回答。

```python
# ❌ auto → DeepSeek 不调工具，凭记忆回答（可能是错的）
create_kwargs["tool_choice"] = "auto"

# ❌ required 全程 → 死循环，每轮都被迫调工具，永不结束
create_kwargs["tool_choice"] = "required"

# ✅ 首轮 required、后续 auto → 既保证调工具，又能正常结束
if step == 0:
    create_kwargs["tool_choice"] = "required"
else:
    create_kwargs["tool_choice"] = "auto"
```

### 3. 为什么 model 不硬编码
- `agent_loop.py` 默认值走 `config.MODEL`
- 所有配置统一在 `config.py` → `.env`，一处改全局生效

### 4. tools 数据结构（OpenAI function-calling 格式）
```python
tools = {
    "get_current_time": {
        "handler": async_function,
        "schema": {
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "返回当前的日期和时间",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        }
    }
}
```

---

## 文件用途速览

| 文件 | 做什么 | 当前状态 |
|------|--------|----------|
| `main.py` | FastAPI 入口，`/health` + `POST /agent`，注册 6 个工具 | ✅ |
| `agent_loop.py` | Agent 核心循环，含超时 + Rich + LLM 异常处理 | ✅ |
| `config.py` | 读 `.env` 加载配置 | ✅ |
| `prompts.py` | 系统 Prompt 模板（含 6 工具使用指引） | ✅ |
| `rich_display.py` | Rich 终端美化，TTY 自动检测降级，全 ASCII 安全 | ✅ |
| `requirements.txt` | 项目完整依赖清单（11 个包） | ✅ |
| `tools/get_time.py` | `get_current_time` 工具 | ✅ |
| `tools/file_tools.py` | `write_file` / `read_file` / `list_files`（3合1） | ✅ |
| `tools/rag_search.py` | RAG 检索工具，对接项目一 Chroma | ✅ |
| `tools/web_search.py` | DuckDuckGo 免费网页搜索（用 `ddgs` 库） | ✅ |
| `tools/__init__.py` | 工具模块入口 | 空 |
| `tests/__init__.py` | 测试模块入口 | 空 |
| `.env` | API Key + 配置（Git 忽略） | 已配 DeepSeek |
| `.env.example` | 配置模板（提交 Git） | ✅ |
| `.gitignore` | 忽略 .venv、.env、__pycache__ 等 | 完成 |

---

## Agent Loop 核心流程（当前实现）

```
用户输入 → POST /agent
  ↓
messages = [{"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}]
  ↓
for step in range(max_iterations):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools_schema,
        tool_choice="required" if step == 0 else "auto"  ← 关键！
    )
    ↓
    if finish_reason == "stop":
        return message.content  →  任务完成 ✅
    ↓
    if finish_reason == "tool_calls":
        messages.append(assistant_message)
        for tool_call in message.tool_calls:
            args = json.loads(tool_call.function.arguments)  ← OpenAI 是 JSON 字符串
            output = await tools[name]["handler"](**args)
        messages.append({"role": "tool", "tool_call_id": ..., "content": output})
        → 继续循环
```

跟 Anthropic SDK 的差异：
- **system prompt** 是 messages[0]，不是独立参数
- **arguments** 是 JSON 字符串，需 `json.loads()`（Anthropic 直接是 dict）
- **stop_reason** → `finish_reason`，`tool_use` → `tool_calls`
- **工具结果** 用 `{"role": "tool", ...}` 而非 `{"type": "tool_result", ...}`

---

## 当前已注册的工具（6个）

| 工具名 | 文件 | 功能 | 参数 |
|--------|------|------|------|
| `get_current_time` | `tools/get_time.py` | 返回当前时间 | 无 |
| `write_file` | `tools/file_tools.py` | 写文本到文件 | `path`, `content` |
| `read_file` | `tools/file_tools.py` | 读文本文件（UTF-8） | `path` |
| `list_files` | `tools/file_tools.py` | 列出目录内容 | `directory`(可选) |
| `rag_search` | `tools/rag_search.py` | 搜项目一知识库 | `query`, `top_k`(可选) |
| `web_search` | `tools/web_search.py` | DuckDuckGo 网页搜索 | `query`, `max_results`(可选) |

---

## 测试方式（PowerShell）

```powershell
# 1. 启动服务（终端 ①）
python main.py

# 2. 测试时间 + 写文件
$body = '{"message": "现在几点了？把时间保存到 time.txt"}'
Invoke-WebRequest -Uri http://127.0.0.1:8000/agent -Method POST -ContentType "application/json" -Body $body -UseBasicParsing

# 3. 测试读取文件
$body = '{"message": "读取 time.txt 的内容"}'
Invoke-WebRequest -Uri http://127.0.0.1:8000/agent -Method POST -ContentType "application/json" -Body $body -UseBasicParsing

# 4. 测试知识库
$body = '{"message": "知识库里有哪些内容？"}'
Invoke-WebRequest -Uri http://127.0.0.1:8000/agent -Method POST -ContentType "application/json" -Body $body -UseBasicParsing

# 5. 测试网页搜索
$body = '{"message": "搜索 Python asyncio 最新教程"}'
Invoke-WebRequest -Uri http://127.0.0.1:8000/agent -Method POST -ContentType "application/json" -Body $body -UseBasicParsing

# 6. 测试多工具联动（搜+写）
$body = '{"message": "搜一下 FastAPI 特性，总结后保存到 fastapi-summary.md"}'
Invoke-WebRequest -Uri http://127.0.0.1:8000/agent -Method POST -ContentType "application/json" -Body $body -UseBasicParsing
```

**注意：** PowerShell 里不要用 `curl`（被别名成了 Invoke-WebRequest 但参数不兼容），用 `$body` 变量方式最稳。

---

## 项目一对接信息

| 项目 | 值 |
|------|------|
| Chroma DB 路径 | `../AI_Agent_Project/chroma_db/` |
| 集合名 | `my_rag_collection`（53 条文档） |
| Embedding 模型 | `paraphrase-multilingual-MiniLM-L12-v2` |
| 距离度量 | cosine |

---

## 添加新工具的标准方式（当前规范）

```python
# 1. 写工具文件 tools/xxx.py
async def my_tool(param: str) -> str:
    return f"结果: {param}"

# OpenAI function-calling schema 格式
MY_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "my_tool",
        "description": "工具描述",
        "parameters": {
            "type": "object",
            "properties": {
                "param": {"type": "string", "description": "参数说明"}
            },
            "required": ["param"]
        }
    }
}

# 2. 在 main.py 里注册
from tools.xxx import my_tool, MY_TOOL_SCHEMA
tools["my_tool"] = {"handler": my_tool, "schema": MY_TOOL_SCHEMA}
```

### 配置文件 `.env`
```
ANTHROPIC_API_KEY=sk-xxx            # API Key（名称保留兼容，值填 DeepSeek 的）
LLM_BASE_URL=https://api.deepseek.com  # 换成千问/智谱就是另一套
MODEL=deepseek-chat                 # 模型名
MAX_TOKENS=4096
MAX_ITERATIONS=10
TOOL_TIMEOUT=30
```

---

## 第 4 天新增内容

### 容错机制
- **工具超时**：`asyncio.wait_for(handler(**args), timeout=config.TOOL_TIMEOUT)` → 30 秒超时
- **LLM API 异常**：`try/except` 包裹 `create()` 调用，网络故障不崩
- **分层异常**：TimeoutError → KeyError → Exception，逐层精确捕获
- **Rich 输出**：`rich_display.py` 模块，TTY 自动检测，非终端降级为 print()

### Rich 显示效果（全 ASCII 安全，避免 Windows GBK 编码问题）
```
┌ Agent 推理 ──────────────────────────────┐
│ Thinking (round 1/10)                     │
│ Tools: get_current_time, write_file...    │
└───────────────────────────────────────────┘
  > web_search({"query": "Python asyncio"})
  OK web_search -> search results: 5 items
  Agent Response: ...
```

### 第 4 天踩坑记录
- **Windows GBK vs emoji**：`rich_display.py` 和 `web_search.py` 所有 emoji 必须换成 ASCII 字符（`OK`/`FAIL`/`>`），否则 `print()` 在 Windows 终端抛 `UnicodeEncodeError`
- **`duckduckgo_search` → `ddgs`**：原包已重命名，最新版本用 `from ddgs import DDGS`
- **web_search 网络问题**：`ddgs` 后端走 Yahoo/Bing，中国大陆可能超时。代码层面已做超时捕获，但工具是否可用取决于网络环境
- **异常捕获顺序**：`asyncio.TimeoutError` 是 `Exception` 的子类，必须写在前面的 `except` 分支，否则永远匹配不到（经典 Python 面试题）

---

## 下一步做什么

1. **🔴 当前任务**：写 `tools/weather.py` —— 天气查询工具，用免费 API `wttr.in`（不需要 API Key）
2. **第 5 天**：SSE 流式改造、`static/agent.html` 前端
3. **第 6 天**：pytest 测试、README
4. **第 7 天**：演示视频、简历描述

---

## 当前会话上下文（2026-07-28）

### 用户学习状态
- 用户处于学习阶段，已逐行理解第 4 天所有代码
- 理解核心概念：`isatty()` 检测、`asyncio.to_thread` 包裹同步代码、异常捕获顺序
- 下一步计划：用户自己写 `tools/weather.py`，Claude review

### 天气工具规格（待实现）
- **API**：`wttr.in`，免费无需注册，URL 格式 `https://wttr.in/{city}?format=j1`
- **函数签名**：`async def get_weather(city: str) -> str`
- **HTTP 库**：用 `aiohttp`（项目已安装）
- **Schema**：`GET_WEATHER_SCHEMA`，参数 `city`（必填）
- **注册**：在 `main.py` 的 tools dict 中加入
- **参考模板**：`tools/web_search.py`（结构最接近——都是 HTTP 请求 + JSON 解析）

### 工具总数：6 → 目标 7
当前 6 个：get_current_time, write_file, read_file, list_files, rag_search, web_search
