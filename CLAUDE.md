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
| `agent_loop.py` | **OpenAI SDK 原生 tool use**，核心循环完整（含超时+Rich+事件驱动） | ✅ |
| `tools/get_time.py` | 第 1 天假工具，验证循环能跑 | ✅ |
| `tools/file_tools.py` | write_file / read_file / list_files 工具（3合1） | ✅ |
| `tools/rag_search.py` | 第 3 天 RAG 知识库检索，对接项目一 Chroma 向量库 | ✅ |
| `tools/web_search.py` | 第 4 天 DuckDuckGo 免费网页搜索 | ✅ |
| `tools/weather.py` | 高德天气 API（实时 + 预报）—— 用户自己写的 | ✅ |
| `rich_display.py` | 第 4 天 Rich 终端美化（TTY 自动检测降级） | ✅ |
| `requirements.txt` | 第 4 天 项目完整依赖清单 | ✅ |
| `main.py` | `GET /health` + `POST /agent`（SSE 流式），注册 7 个工具 + 挂载静态文件 | ✅ |
| `config.py` | 从 `.env` 加载配置，支持 OpenAI 兼容服务（DeepSeek 等） | ✅ |
| `prompts.py` | 系统 Prompt 模板（含 7 工具使用指引） | ✅ |
| `static/agent.html` | 第 5 天 Agent 思考可视化前端（SSE 消费 + Round 卡片） | ✅ |
| `static/index.html` | 入口跳转页 → `/agent.html` | ✅ |

### 🔲 待完成

| 天数 | 任务 | 状态 |
|------|------|------|
| 第 1 天 | 项目骨架 + Agent Loop 最小原型 + curl 验证 | ✅ |
| 第 2 天 | 正式对接 LLM API tool use + write_file 工具 | ✅ |
| 第 3 天 | 接入项目一 RAG 知识库（rag_search） | ✅ |
| 第 4 天 | 更多工具（Web Search + File）+ 容错 + Rich 输出 | ✅ |
| 第 5 天 | 前端 SSE 流式 + Agent 思考可视化 | ✅ |
| 第 6 天 | pytest + README + **前端重新设计** | 🔲 |
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
| `main.py` | FastAPI 入口，`/health` + `POST /agent`（SSE 流式），注册 7 个工具，挂载 static/ | ✅ |
| `agent_loop.py` | Agent 核心循环，事件驱动（6 种事件）+ `run_stream()` generator + Rich 消费 | ✅ |
| `config.py` | 读 `.env` 加载配置 | ✅ |
| `prompts.py` | 系统 Prompt 模板（含 7 工具使用指引） | ✅ |
| `rich_display.py` | Rich 终端美化，TTY 自动检测降级，全 ASCII 安全 | ✅ |
| `requirements.txt` | 项目完整依赖清单（11 个包） | ✅ |
| `static/agent.html` | Agent 思考可视化前端（~320 行），SSE 消费 + Round 卡片 | ✅ |
| `static/index.html` | 入口跳转 → agent.html | ✅ |
| `tools/get_time.py` | `get_current_time` 工具 | ✅ |
| `tools/file_tools.py` | `write_file` / `read_file` / `list_files`（3合1） | ✅ |
| `tools/rag_search.py` | RAG 检索工具，对接项目一 Chroma | ✅ |
| `tools/web_search.py` | DuckDuckGo 免费网页搜索（用 `ddgs` 库） | ✅ |
| `tools/weather.py` | 高德天气 API（实时 + 预报） | ✅ |
| `tools/__init__.py` | 工具模块入口 | 空 |
| `tests/__init__.py` | 测试模块入口 | 空 |
| `.env` | API Key + 配置（Git 忽略） | 已配 DeepSeek |
| `.env.example` | 配置模板（提交 Git） | ✅ |
| `.gitignore` | 忽略 .venv、.env、__pycache__、测试产物 | ✅ |

---

## 第 5 天新增内容（2026-07-28）

### 核心架构变更：事件驱动 + SSE 流式

**问题：** 原来 `/agent` 是 `return {"result": "..."}` 一把梭，用户看不到 Agent 中间干了什么。

**方案：** 引入事件流抽象层 —— Agent Loop yield 事件对象，SSE 和 Rich 终端各自消费。

### 架构图

```
                    run_stream()  async generator
                   ┌──────────┐
用户输入 ──→ Agent │ yield ThinkingEvent  │
  POST /agent      │ yield ToolCallEvent  │──→ SSE (浏览器)
                   │ yield ToolResultEvent│──→ Rich (终端)
                   │ yield TextEvent      │
                   │ yield DoneEvent      │
                   └──────────┘
```

### 6 种事件类型（`agent_loop.py` 第 19-62 行）

| 事件 | 字段 | 触发时机 |
|------|------|---------|
| `ThinkingEvent` | step, max_steps, tools | 每轮推理开始 |
| `ToolCallEvent` | tool, args | 准备调工具 |
| `ToolResultEvent` | tool, success, output | 工具执行完毕 |
| `TextEvent` | content | 最终回复 |
| `DoneEvent` | — | 任务正常完成 |
| `ErrorEvent` | message | 出错 |

### `agent_loop.py` 改动

- **第 19-62 行**：新增 6 个事件 dataclass + `AgentEvent` 联合类型
- **第 97-120 行**：`run()` 重写为消费 `run_stream()` 事件 + 驱动 Rich 终端
- **第 122-260 行**：新增 `run_stream()` async generator（原 `run()` 逻辑搬过来，所有输出改为 `yield` 事件）

### `main.py` 改动

- `POST /agent` 返回 `StreamingResponse(text/event-stream)` 代替 `{"result": "..."}`
- 事件对象 → CamelCase→snake_case 转换 → JSON → `data: {...}\n\n`
- `use_rich=False` 固定关闭 HTTP 模式的 Rich 输出
- 取消注释，启用 `app.mount("/", StaticFiles(directory="static", html=True))`

### `static/agent.html` 前端

- 单文件 ~320 行：暗色主题 + SSE fetch+reader + 6 种事件处理
- 用户消息靠右气泡，Agent 思考过程为左侧 Round 卡片（可折叠）
- 工具调用显示 ▶ 图标 + 参数，结果显示 ✔/✘ + 摘要
- 最终回答以独立卡片展示

### 踩坑记录

- **端口占用**：测试时旧服务占 8000 端口，新代码没生效，返回的还是 JSON。需要 `taskkill` 后重启
- **事件名 CamelCase**：`ToolCallEvent` → `toolcall`（错），加了 `re.sub(r'(?<!^)(?=[A-Z])', '_', raw_name).lower()` 转成 `tool_call`
- **`html=True` 冲突风险**：`app.mount("/", StaticFiles(html=True))` 会让 `GET /agent` 被静态文件拦截。当前安全因为 API 是 POST。如果以后加 GET /agent 需要改名或拆分路由
- **rag_search 编码问题**：rag_search 返回含 emoji 时在 Windows GBK 下抛 `UnicodeEncodeError`，是已知旧 bug，非第 5 天引入

---

## 第 6 天前端重设计方案（调研完成，待实现）

### 调研对象

DeepSeek、豆包、通义千问的网页版 UI 设计。

### 主流设计共性

| 特征 | DeepSeek | 豆包 | 千问 |
|------|----------|------|------|
| **布局** | 左侧竖导航 + 主对话区 | 左侧边栏三分区 + 对话区 | 侧边栏 + 悬浮球 |
| **配色** | 深色为主、语义色克制 | 极简、温暖 | 极简融合浏览器 |
| **对话** | 无多余装饰、卡片分层 | 无头像、干净 | 嵌入式 |
| **输入框** | 底部左角放模型切换 | `/` `@` 快捷调用 | 多个快捷入口 |
| **特色** | IDE 级代码块、模式选择器 | 情感化引导、预判交互 | 六种桌面套件 |

**共同点：极简克制、左侧导航、深色主题、输入框集成快捷能力。**

### 改造方向

跟当前前端（项目一风格）的核心区别：

| | 当前 agent.html | 改造后 |
|------|------|------|
| 布局 | 纯聊天，无导航 | **左侧工具栏** + 主区域 |
| 工具可见性 | 无 | **7 个工具以图标展示在侧边栏** |
| Agent 思考 | 折叠 Round 卡片 | **时间线步骤 + 进度条** |
| 配色 | 红黑（`#e94560`） | **蓝灰主色调**（更接近 DeepSeek） |
| 输入框 | 纯文本框 | 下方带工具快捷标签 |
| 头像 | emoji 图标 | 无头像（学豆包） |

### 目标视觉草图

```
┌──────────┬─────────────────────────────────────────┐
│          │  🤖 Agent 工作台                         │
│  🏠 首页  ├─────────────────────────────────────────┤
│          │                                         │
│  📋 工具  │  用户: 搜 Python decorator 并保存       │
│  ──────  │                                         │
│  🕐 时间  │  ┌─ Agent 执行过程 ──────────────────┐  │
│  ✍️ 写文件│  │ Step 1  搜索                      │  │
│  📖 读文件│  │  ├ web_search ✓ (1.2s)            │  │
│  📂 列目录│  │  └ 找到 5 条结果                  │  │
│  🔍 知识库│  │ Step 2  保存                      │  │
│  🌐 搜索  │  │  ├ write_file ✓ (0.3s)            │  │
│  🌤️ 天气  │  │  └ 写入成功, 2.3 KB               │  │
│          │  └────────────────────────────────────┘  │
│  📜 历史  │                                         │
│  · 上次   │  ✨ Python decorator 总结已保存到       │
│  · 更早   │     decorator.md，包含...              │
│          │                                         │
│          ├─────────────────────────────────────────┤
│          │  [输入任务...]              ⚡ /工具     │
│          │  get_current_time | write_file | ...    │
└──────────┴─────────────────────────────────────────┘
```

---

## Agent Loop 核心流程（当前实现）

```
用户输入 → POST /agent (SSE StreamingResponse)
  ↓
messages = [{"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}]
  ↓
for step in range(max_iterations):
    yield ThinkingEvent(step, max_steps, tools)  ← 推给 SSE
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools_schema,
        tool_choice="required" if step == 0 else "auto"  ← 关键！
    )
    ↓
    if finish_reason == "stop":
        yield TextEvent(content=message.content)  →  DoneEvent()
    ↓
    if finish_reason == "tool_calls":
        messages.append(assistant_message)
        for tool_call in message.tool_calls:
            yield ToolCallEvent(...)              ← SSE 事件
            args = json.loads(tool_call.function.arguments)
            output = await tools[name]["handler"](**args)
            yield ToolResultEvent(...)            ← SSE 事件
        messages.append({"role": "tool", "tool_call_id": ..., "content": output})
        → 继续循环
```

跟 Anthropic SDK 的差异：
- **system prompt** 是 messages[0]，不是独立参数
- **arguments** 是 JSON 字符串，需 `json.loads()`（Anthropic 直接是 dict）
- **stop_reason** → `finish_reason`，`tool_use` → `tool_calls`
- **工具结果** 用 `{"role": "tool", ...}` 而非 `{"type": "tool_result", ...}`

---

## 当前已注册的工具（7个）

| 工具名 | 文件 | 功能 | 参数 |
|--------|------|------|------|
| `get_current_time` | `tools/get_time.py` | 返回当前时间 | 无 |
| `write_file` | `tools/file_tools.py` | 写文本到文件 | `path`, `content` |
| `read_file` | `tools/file_tools.py` | 读文本文件（UTF-8） | `path` |
| `list_files` | `tools/file_tools.py` | 列出目录内容 | `directory`(可选) |
| `rag_search` | `tools/rag_search.py` | 搜项目一知识库 | `query`, `top_k`(可选) |
| `web_search` | `tools/web_search.py` | DuckDuckGo 网页搜索 | `query`, `max_results`(可选) |
| `get_weather` | `tools/weather.py` | 高德天气（实时+预报） | `city` |

---

## 测试方式（PowerShell）

```powershell
# 1. 启动服务（终端 ①）
python main.py

# 2. 浏览器打开
# http://127.0.0.1:8000/

# 3. SSE 流式测试（PowerShell）
$body = '{"message": "现在几点了？"}'
$response = Invoke-WebRequest -Uri http://127.0.0.1:8000/agent -Method POST -ContentType "application/json" -Body $body -UseBasicParsing
$response.Content
# 应该看到多行 data: {"type": "thinking", ...} 等 SSE 事件
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

## 第 4 天踩坑记录

- **Windows GBK vs emoji**：`rich_display.py` 和 `web_search.py` 所有 emoji 必须换成 ASCII 字符（`OK`/`FAIL`/`>`），否则 `print()` 在 Windows 终端抛 `UnicodeEncodeError`
- **`duckduckgo_search` → `ddgs`**：原包已重命名，最新版本用 `from ddgs import DDGS`
- **web_search 网络问题**：`ddgs` 后端走 Yahoo/Bing，中国大陆可能超时。代码层面已做超时捕获，但工具是否可用取决于网络环境
- **异常捕获顺序**：`asyncio.TimeoutError` 是 `Exception` 的子类，必须写在前面的 `except` 分支，否则永远匹配不到（经典 Python 面试题）

---

## 下一步做什么

1. **第 6 天**：pytest 测试 + README + **前端重新设计**（左侧工具栏 + 蓝灰配色 + 时间线步骤）
2. **第 7 天**：演示视频、简历描述

---

## 当前会话上下文（2026-07-28）

### 第 5 天完成
- `agent_loop.py`：新增 6 种事件 dataclass + `run_stream()` async generator + `run()` 改为事件消费驱动 Rich
- `main.py`：`POST /agent` → SSE `StreamingResponse` + 挂载 `static/`
- `static/agent.html`：~320 行前端，暗色主题 + SSE 消费 + Round 卡片 + 工具调用可视化
- `static/index.html`：入口跳转 → agent.html
- `.gitignore`：新增 `current-time.txt`

### 第 6 天前端重设计划（调研完成）
- 调研了 DeepSeek、豆包、千问的 UI 设计
- 核心方向：左侧工具栏 + 蓝灰主色调 + 时间线步骤 + 输入框工具快捷提示
- 目标：跟项目一的 chat.html 拉开视觉差距，更像专业 Agent 工作台

### 当前 7 个工具
get_current_time, write_file, read_file, list_files, rag_search, web_search, get_weather
