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
| `static/agent.html` | 第 5 天 Agent 思考可视化前端（SSE 消费 + Round 卡片）→ 第 6 天重构为侧栏+蓝灰+时间线 | ✅ |
| `static/index.html` | 入口跳转页 → `/agent.html` | ✅ |
| **pytest 测试** | 22 条测试（11 agent_loop + 8 tools + 3 config），全部通过 | ✅ |
| **README.md** | 完整项目文档：架构图、快速开始、API 文档、工具扩展指南 | ✅ |
| **前端重构** | 侧栏工具导航 + 蓝灰主色调 + 时间线步骤 + 工具快捷标签 | ✅ |

### 🔲 待完成

| 天数 | 任务 | 状态 |
|------|------|------|
| 第 1 天 | 项目骨架 + Agent Loop 最小原型 + curl 验证 | ✅ |
| 第 2 天 | 正式对接 LLM API tool use + write_file 工具 | ✅ |
| 第 3 天 | 接入项目一 RAG 知识库（rag_search） | ✅ |
| 第 4 天 | 更多工具（Web Search + File）+ 容错 + Rich 输出 | ✅ |
| 第 5 天 | 前端 SSE 流式 + Agent 思考可视化 | ✅ |
| 第 6 天 | pytest + README + **前端重新设计** | ✅ |
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
| `tests/conftest.py` | 共享 fixture + mock 辅助函数 | ✅ 第 6 天 |
| `tests/test_agent_loop.py` | Agent Loop 核心测试（11 条） | ✅ 第 6 天 |
| `tests/test_tools.py` | 工具独立测试（8 条） | ✅ 第 6 天 |
| `tests/test_config.py` | 配置测试（3 条） | ✅ 第 6 天 |
| `pytest.ini` | pytest 配置（asyncio_mode=auto） | ✅ 第 6 天 |
| `README.md` | 项目文档（架构+快速开始+API+扩展指南） | ✅ 第 6 天 |
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

1. ~~**第 6 天**：pytest 测试 + README + 前端重新设计~~ ✅ 已完成
2. **第 7 天**：演示视频（录制 2-3 个场景）+ 简历描述（已写好两版）+ 面试准备（已写好 7 道常见问答）

---

## 第 6 天新增内容（2026-07-29）

### pytest 测试（22 条，全部通过）

```
tests/
├── conftest.py            # 共享 fixture: mock_llm_client, echo_tool, agent_loop_factory
│                          # mock 辅助: make_text_response(), make_tool_calls_response()
├── test_agent_loop.py     # 11 条: 单/多工具调用, 直接文本, API 错误, 超时,
│                          #         未知工具, 工具异常, JSON 解析回退, 空输入, 上限
├── test_tools.py          # 8 条: 时间格式, 文件读写, 目录列表, 搜索/天气(Skip on fail)
└── test_config.py         # 3 条: 默认值, API Key 类型, 数值类型
```

运行: `pytest tests/ -v`

### 前端重构（`static/agent.html`）

**布局**: 左侧 240px 工具栏 + 主对话区域（CSS Grid→Flexbox 两栏）
**配色**: 红黑 `#e94560` → 蓝灰 `#4f8cff`（更接近专业工具风格）
**Sidebar**: 导航区 + 7 个工具列表（带绿色状态灯）
**Agent 思考**: Round 折叠卡片 → 垂直时间线（时间线节点 + 竖线连接）
**输入框**: 新增 7 个工具快捷标签，点击插入工具名到输入框
**响应式**: <700px 隐藏侧栏

### README.md

包含: 架构 ASCII 图, 快速开始, API 文档, SSE 事件协议表, 7 工具表格, 添加新工具指南,
项目结构, 技术栈, 与项目一的对比

### 踩坑记录

- **test_agent_loop import**: `from conftest import ...` 在 pytest 里需要写成 `from tests.conftest import ...`
- **weather test**: 高德 API `city="Beijing"` 返回空字符串，必须用中文 `city="北京"`
- **MagicMock model_dump()**: `make_tool_calls_response` 必须显式设置 `choice.message.model_dump.return_value`，否则 Agent Loop 的 `messages.append(choice.message.model_dump())` 拿不到数据

---

## 当前会话上下文（2026-07-29）

### 第 6 天完成
- **测试**: 22 条 pytest（tests/conftest.py + test_agent_loop.py + test_tools.py + test_config.py），全部通过
- **README**: 完整项目文档（架构图 + 快速开始 + API + 工具扩展指南）
- **前端重构**: 侧栏工具导航 + 蓝灰 `#4f8cff` 主色调 + 时间线步骤 + 7 个工具快捷标签 + 响应式
- **CLAUDE.md**: 更新开发进度 + 文件清单 + 踩坑记录

### 当前 7 个工具
get_current_time, write_file, read_file, list_files, rag_search, web_search, get_weather

---

## 第 7 天：简历描述 + 面试准备 + 演示视频

### 一、简历项目描述（可直接用）

#### 版本 A：单项目版（项目二独立描述）

```
项目名称：AI 工作流 Agent 引擎 —— 自然语言驱动的多工具编排系统
时间：2026.07-2026.08 | 独立开发
技术栈：Python / FastAPI / OpenAI SDK / SSE / ChromaDB / DuckDuckGo

项目描述：
基于大语言模型自研的智能体引擎。不依赖 LangChain/CrewAI 等框架，基于 OpenAI
SDK 裸写 Agent 核心循环，让 Agent 能自主理解自然语言任务、制定执行计划、调度
多种工具完成复杂工作流。

核心工作：
- 自研 Agent Loop：Observe→Plan→Act 循环，手动实现 tool calling、消息历史
  管理、异常容错、最大轮次保护
- 可插拔工具系统（7 个工具）：时间查询、本地文件读写、目录浏览、RAG 知识库
  检索、DuckDuckGo 网页搜索、高德天气 API
- 跨项目知识库共享：复用项目一 ChromaDB 向量库，将 RAG 检索作为 Agent 工具
- SSE 流式可视化：自研 6 种事件类型（thinking/tool_call/tool_result/text/
  done/error），前端时间线实时展示 Agent 完整思考链路
- 容错机制：工具超时重试、未知工具回退、非法 JSON 参数兜底、最大轮次保护

项目成果：
- 22 条 pytest 测试，全部通过
- 完整项目文档（README + CLAUDE.md）
- 前端：左侧工具栏 + 蓝灰配色 + 时间线可视化 + 7 个工具快捷标签
```

#### 版本 B：两个项目串联版（推荐，放简历项目经历栏）

```
项目经历

项目一：RAG 知识库智能问答系统 | 2026.07 | 独立开发
技术栈：Python / FastAPI / ChromaDB / sentence-transformers / SSE / MCP

- 从零构建 RAG 完整管道：文档解析→文本分块→向量化入库→语义检索→LLM 生成
- 53 条技术文档入库，ChromaDB 持久化存储，embedding 模型 paraphrase-multilingual-MiniLM-L12-v2
- 使用 MCP 协议将 RAG 检索封装为标准化工具，可被任何 MCP 客户端调用
- SSE 流式前端 Chat UI，展示来源引用和相关度评分

项目二：AI 工作流 Agent 引擎 | 2026.08 | 独立开发
技术栈：Python / FastAPI / OpenAI SDK / SSE / ChromaDB / DuckDuckGo

- 自研 Agent Loop 核心循环，不依赖 LangChain/CrewAI，理解每一步原理
- 7 个可插拔工具：时间、文件读写、目录、跨项目 RAG 检索、网页搜索、天气
- 复用项目一 ChromaDB 知识库，跨项目共享基础设施
- SSE 流式事件驱动（6 种事件），前端时间线可视化 Agent 完整思考链路
- 22 条 pytest 测试，完整的错误处理和超时保护
```

### 二、面试准备：常见问题 + 回答要点

#### Q1: "为什么不用 LangChain/CrewAI？"

回答要点：
1. **学习目的**: 这个项目的目标就是理解 Agent 底层原理。用 LangChain 一行代码
   `create_react_agent()` 就完了，但面试官问你"Agent Loop 里面发生了什么"你答不上来
2. **控制力**: 框架封装太深，出问题时不知道是模型问题还是框架 bug。
   自己写 loop，每一行的行为完全可控
3. **面试差异化**: 人人都会调 LangChain，但能手写 Agent Loop 的人少得多。
   这也体现你对 LLM 工作原理的理解深度
4. **实际体感**: 自己写 loop 代码量并不大，agent_loop.py 核心也就 150 行。
   关键是理解流程，不是代码量

#### Q2: "Agent Loop 的核心流程是什么？"

回答要点：
```
1. 用户输入 → 拼到 messages 里
2. 循环开始 (for step in range(max_iterations)):
   a. 把 messages + tools schema 发给 LLM
   b. LLM 返回 finish_reason:
      - "stop" → 任务完成，输出最终文本，退出循环
      - "tool_calls" → 解析工具名+参数，执行工具处理器
   c. 工具结果追加到 messages（role: "tool"）
   d. 继续下一轮，LLM 能看到之前的工具调用和结果
3. 达到 max_iterations 上限 → 返回错误，防止死循环烧钱
```

关键细节要强调：
- tool_choice 首轮 "required"、后续 "auto"（DeepSeek 踩坑经验）
- messages 积累式设计：每轮 LLM 都能看到完整历史
- 异常处理三层：API 调用异常、工具执行异常、未知工具

#### Q3: "两个项目怎么串联的？"

回答要点：
```
"项目一是 RAG 系统，我把它做成了一个独立的检索服务，用 MCP 协议暴露给外部 Agent 调用。
项目二是 Agent 引擎，我把项目一的 ChromaDB 向量库当做一个检索工具（rag_search）
注册到 Agent 的工具列表里。

当用户问知识库里的问题时，Agent 自主决定调用 rag_search 工具检索文档，
拿到结果后再决定是直接回答、还是结合其他工具进一步处理。

两个项目共享同一套 ChromaDB 基础设施，形成了完整的 Agent 工具生态闭环：
项目一提供知识，项目二负责执行和编排。"
```

#### Q4: "OpenAI SDK vs Anthropic SDK 你怎么看？为什么切了？"

回答要点：
1. 原计划用 Anthropic SDK（开发计划就是这么写的），但用户只有 DeepSeek API Key
2. DeepSeek 兼容 OpenAI 协议，Anthropic API 不接受 sk- 格式的 key
3. 切到 OpenAI SDK + base_url 后，同一套代码能对接 DeepSeek/千问/智谱等任意国产模型
4. 面试价值：选 OpenAI 协议意味着不绑定厂商，面试时可以展开讲"为什么选开放协议"
5. 两个 SDK 的 tool use 差异：system prompt 位置、arguments 格式（字符串 vs dict）、
   finish_reason vs stop_reason、工具结果的 messages 格式

#### Q5: "SSE 流式是怎么设计的？为什么用 6 种事件？"

回答要点：
1. 问题背景：原来 `/agent` 是 `return {"result": "..."}` 一把梭，
   用户看不到 Agent 中间干了什么（调了哪个工具、结果怎样）
2. 方案：在 Agent Loop 和表现层之间插入事件流抽象层
   - Agent Loop 不再直接 print 或 return，而是 yield 事件对象
   - SSE 和 Rich 终端各自消费同一套事件流
3. 6 种事件：thinking（推理开始）、tool_call（准备调工具）、
   tool_result（执行结果）、text（最终回答）、done（完成）、error（出错）
4. 好处：前端能看到 Agent 每一步在干什么，不是黑盒

#### Q6: "DeepSeek 踩过什么坑？"

回答要点：
1. **tool_choice 策略**: DeepSeek 在 auto 模式不主动调工具，凭记忆回答。
   解决方案：首轮 required、后续 auto
2. **debug 困难**: DeepSeek 有时返回的 tool arguments 是非法 JSON，
   不做兜底会直接崩溃。加了 try/except + 回退为 {} 的处理
3. **这不是 DeepSeek 的问题**，是国产模型普遍特点。反而说明你做的是"通用方案"
   而非"绑定一家"——这才是面试加分项

#### Q7: "容错机制怎么设计的？"

回答要点：
1. **LLM API 调用**: try/except 捕获，yield ErrorEvent，不崩溃
2. **工具执行超时**: asyncio.wait_for(handler(**args), timeout=30s)
3. **未知工具**: KeyError 捕获，返回"工具 XXX 不存在，可用工具：[列表]"
4. **工具执行异常**: RuntimeError 等通用异常捕获，把错误信息返回给 LLM
5. **JSON 解析失败**: json.loads() 的 JSONDecodeError → 回退为 {}
6. **最大轮次保护**: for 循环 + max_iterations，防止死循环烧钱
7. **异常捕获顺序**: asyncio.TimeoutError 必须写在 Exception 前面
   （经典 Python 面试题）

### 三、演示视频脚本（2-3 分钟）

#### 场景 1：查时间 + 保存文件（30 秒）
```
输入：现在几点了？保存到 time.txt

展示效果：
- Step 1: get_current_time → 返回时间
- Step 2: write_file → 写入成功
- 最终回答：已保存

面试话术："这个是最基础的 Agent 调用链，验证了工具编排和多步骤执行。"
```

#### 场景 2：搜索 + 总结 + 写报告（60 秒）
```
输入：搜索 Python asyncio 最佳实践，总结保存到 asyncio_guide.md

展示效果：
- Step 1: web_search("Python asyncio 最佳实践") → 5 条结果
- Step 2: write_file("asyncio_guide.md", 总结内容) → 写入成功

面试话术："Agent 自主完成了搜资料→总结→写报告的完整工作流。"
```

#### 场景 3：知识库检索 + 联网补充（60 秒）
```
输入：知识库里关于 RAG 的内容有哪些？再搜一下最新的 RAG 技术进展

展示效果：
- Step 1: rag_search("RAG") → 项目一知识库的文档
- Step 2: web_search("2026 RAG 技术最新进展") → 网络搜索结果
- 综合回答

面试话术："Agent 能同时利用本地知识和实时网页信息，最终给出完整回答。"
```

### 四、简历一句话总结（面试开场用）

> "我做了两个互补的 AI 项目：第一个手搓了 RAG 知识库问答系统并用 MCP 协议暴露服务，
> 第二个进一步手搓了 Agent 引擎，让 LLM 能自主规划任务、组合 7 个工具完成复杂工作流。
> 两个项目都不依赖 LangChain 等框架，从 SDK 裸写，理解每一步原理。"
