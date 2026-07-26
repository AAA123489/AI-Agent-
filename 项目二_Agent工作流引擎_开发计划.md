# 项目二：AI 工作流 Agent —— 自然语言驱动的多工具编排系统

> **定位：** 跟项目一互补。项目一是"把 RAG 做成 Agent 工具"，项目二是"让 Agent 自主规划、调度、组合多个工具"。
>
> **目标：** 不依赖 LangChain/CrewAI，基于 Anthropic SDK 裸写 Agent Loop，理解每一步原理。
>
> **开发周期：** 7 天，每天 2-3 小时。

---

## 进度追踪

| 天数 | 任务 | 状态 |
|------|------|------|
| 第 1 天 | 初始化项目 + Agent Loop 最小原型 | ⬜ |
| 第 2 天 | 工具系统 + 对接 Claude API tool use | ⬜ |
| 第 3 天 | 接入项目一 RAG 知识库 | ⬜ |
| 第 4 天 | 更多工具（Web Search + File + Code） | ⬜ |
| 第 5 天 | 前端页面 + Agent 思考可视化 | ⬜ |
| 第 6 天 | 完善 + 测试 + README | ⬜ |
| 第 7 天 | 演示视频 + 简历项目描述 | ⬜ |

---

## 第 1 天：搭骨架 —— 初始化项目 + 跑通最小 Agent Loop

### 目标

新建项目文件夹，搭好目录结构，写出第一个能跑通的 "Hello World Agent"。

### 要做的事

**1. 初始化项目**
```bash
mkdir AI_Agent_Project2
cd AI_Agent_Project2
python -m venv .venv
source .venv/Scripts/activate
pip install anthropic fastapi uvicorn aiohttp python-dotenv
```

**2. 目录结构**
```
AI_Agent_Project2/
├── main.py                    # FastAPI 入口（先不写前端，用 curl 调）
├── agent_loop.py              # Agent 核心循环
├── tools/
│   └── __init__.py
├── prompts.py                 # Agent 系统 Prompt
├── config.py                  # 配置管理（API Key 等）
├── requirements.txt
└── .env.example
```

**3. 核心要手写的东西 —— Agent Loop**

这是整个项目的心脏。流程就三步：

```
用户输入一句话
  ↓
Agent Loop 开始 ──→  LLM 分析任务，决定下一步做什么
    ↑                        ↓
    │                 LLM 返回：调用工具 OR 给出最终答案
    │                        ↓
    └── 工具执行结果 ←── 如果需要调用工具，执行工具函数

如果 LLM 说"任务完成" → 跳出循环，返回结果
```

**不需要很多代码，agent_loop.py 大概 80-100 行：**
- `class AgentLoop`：接收 system_prompt + tools + max_iterations
- `async run(user_input)` → 循环调用 LLM，直到 LLM 说 stop 或达到最大轮次
- 每轮把工具执行结果追加到 messages，让 LLM 看到"刚才做了什么"

**4. 写一个假工具验证循环能跑**

先不接真实工具。搞一个 `get_current_time` 文本工具，让 LLM 能"查时间"：

```python
def get_current_time() -> str:
    """返回当前时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
```

LLM 说"用 get_current_time 工具" → Agent Loop 调用这个函数 → 把结果塞回对话 → LLM 看到结果 → 回答用户。

**5. 验证方式**

```bash
python main.py  # 启动 FastAPI，POST /agent 端点
curl -X POST http://127.0.0.1:8000/agent \
  -H "Content-Type: application/json" \
  -d '{"message": "现在几点了？帮我把当前时间保存到 time.txt"}'
```

Agent 应该：调 get_current_time → 写文件 → 返回 "已保存到 time.txt"

### 技术关键点（面试会问）

- Agent Loop 为什么要设 max_iterations？（防止死循环，LLM 可能在工具不达预期时反复重试）
- 为什么不用 while True？（安全兜底，API 调用花钱）

---

## 第 2 天：正式对接 Claude API 的 tool use

### 目标

把第 1 天自己拼 JSON 的方式，升级为 Anthropic SDK 原生的 tool use。

### 要做的事

**1. 理解 Claude API 的 tool use 流程**

你自己在第 1 天做的事情：手动拼 JSON tool 定义 → LLM 返回 JSON → 手动解析 → 手动执行。SDK 封装了这一整套：

```python
import anthropic

client = anthropic.Anthropic(api_key="...")

response = client.messages.create(
    model="claude-sonnet-5-20251201",
    max_tokens=4096,
    system="你是一个智能助手，可以调用工具完成用户的任务。",
    messages=[{"role": "user", "content": "现在几点了？"}],
    tools=[
        {
            "name": "get_current_time",
            "description": "返回当前的日期和时间",
            "input_schema": {"type": "object", "properties": {}, "required": []}
        }
    ]
)

# response.stop_reason 可能是 "tool_use" 或 "end_turn"
# 如果是 tool_use，response.content 里有 tool_use_block
```

**2. 改写 agent_loop.py**

把第 1 天手写的 JSON 工具定义 → 改为 SDK 的 tools 参数格式。Agent Loop 不变，但 LLM 调用改用 SDK：

```
用户输入 → SDK messages.create(tools=[...]) → 拿到 stop_reason
  → "end_turn"：任务完成，返回文本
  → "tool_use"：解析 tool_use_block，调工具，结果追加到 messages，继续下一轮
```

**3. 定义 2 个真实工具**

| 工具 | 功能 |
|------|------|
| `get_current_time` | 返回当前日期时间 |
| `write_file` | 把文本写入文件（指定路径 + 内容） |

### 验证方式

```
curl 请求："现在几点了？把时间保存到 time.txt"
Agent 应该：get_current_time → write_file → 返回成功
```

---

## 第 3 天：接入项目一的 RAG 知识库

### 目标

复用第一个项目的 Chroma 向量库，让你的 Agent 能检索已有的知识库。

### 要做的事

**1. 把项目一的 RAG 变成一个 Tool**

不引入项目一的代码，而是直接在项目二里写一个轻量的 RAG 检索工具：

```python
# tools/rag_search.py
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer

class RAGSearchTool:
    def __init__(self, chroma_path="../AI_Agent_Project/chroma_db"):
        self.client = PersistentClient(path=chroma_path)
        self.model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    def search(self, query: str, top_k: int = 5) -> str:
        # 向量化 → 检索 → 格式化返回
        ...
```

**不用写完整管道，只需要检索功能。** 因为项目一已经处理好了入库。

**2. 注册到你的 Agent**

```python
agent = AgentLoop(
    system_prompt=...,
    tools=[get_current_time, write_file, rag_search],
    max_iterations=10
)
```

**3. 测试**

```
用户: 知识库里关于 RAG 的内容有哪些？
Agent: 调 rag_search → 拿到文档片段 → 基于片段回答
```

### 跟项目一的衔接（面试话术）

> "第一个项目我把 RAG 做成了独立服务 + MCP 工具。第二个项目我在 Agent 里直接复用了 Chroma 向量库，让 Agent 能检索已有知识。两个项目共享一套知识库基础设施。"

---

## 第 4 天：扩展工具 + 容错

### 目标

把工具从 3 个扩展到 5-6 个，加上容错机制。

### 要做的事

**1. 新增工具**

| 工具 | 功能 |
|------|------|
| `web_search` | 用 requests + DuckDuckGo 搜索网页（免费，不需要 API Key） |
| `read_file` | 读取本地文件内容 |
| `list_files` | 列出指定目录下的文件 |

**2. 容错机制**

- 工具执行超时：`asyncio.wait_for(tool_call, timeout=30)`
- 工具执行失败：catch 异常 → 把错误信息作为工具结果返回给 LLM → LLM 决定重试或放弃
- LLM 返回了不存在的工具名：返回 "工具 XXX 不存在，可用工具：..."

**3. Rich 终端输出（调试用）**

在终端跑的时候用 `rich` 库美化输出：

```
┌─ Agent 思考 ─────────────────────┐
│ 用户想知道 Python 的异步原理      │
│ 计划：搜资料 → 总结 → 写文件     │
└──────────────────────────────────┘
  🔧 调用工具: web_search("Python asyncio")
  ✅ 工具返回 5 条搜索结果
  🔧 调用工具: write_file("python-async.md", content)
  ✅ 写入完成，文件 2.3KB
  ✨ Agent 响应：已完成，报告保存在...
```

### 验证方式

```
用户: 帮我搜一下 "Python asyncio 使用场景"，把结果总结保存到 asyncio.md
Agent: web_search → LLM 总结 → write_file → 完成
```

---

## 第 5 天：把项目一的 chat.html 移植过来，做成 Agent 前端

### 目标

前端能展示 Agent 的完整思考过程，不只是最终答案。

### 要做的事

**1. FastAPI SSE 流式改造**

`POST /agent` 改为 SSE 流式输出。不是只流文本，而是流事件：

```python
yield {"type": "planning", "content": "Agent 计划：步骤1 搜索，步骤2 总结，步骤3 存文件"}
yield {"type": "tool_call", "tool": "web_search", "args": {...}}
yield {"type": "tool_result", "tool": "web_search", "result": "找到 5 条..."}
yield {"type": "thinking", "content": "基于搜索结果，Agent 正在总结..."}
yield {"type": "text", "content": "Python asyncio 是..."}  # 最终回复（流式逐字）
yield {"type": "done"}
```

**2. 前端 `static/agent.html`**

基于项目一的 `chat.html` 改造：
- 保留聊天气泡（用户靠右，Agent 靠左）
- 新增 Agent 思考步骤卡片（计划 → 工具调用 → 工具结果）
- 每条工具调用显示为可折叠的卡片，展开能看到参数和结果

**3. 视觉效果**

```
┌──────────────────────────────────────────┐
│ 👤 用户：调研 Claude Code vs Codex CLI    │
├──────────────────────────────────────────┤
│ 🤖 Agent：制定计划                        │
│   ▸ 搜索 Claude Code 最新信息             │
│   ▸ 搜索 Codex CLI 最新信息               │
│   ▸ 对比分析                              │
│   ▸ 写入 comparison.md                    │
│                                           │
│   [执行中] 搜索 Claude Code...              │
│   [完成] 搜索 Claude Code — 找到 8 条      │
│   [执行中] 搜索 Codex CLI...               │
│   ...                                     │
│                                           │
│   ✨ 报告已保存到 comparison.md (3.2 KB)    │
└──────────────────────────────────────────┘
```

---

## 第 6 天：完善 + 测试 + README

### 要做的事

**1. 错误处理补全**
- LLM API 调用失败重试（3 次，指数退避）
- 工具执行超时（30 秒）
- 用户输入为空 / 超长

**2. 补测试（pytest）**
- test_agent_loop.py：单工具调用、多工具联动、异常处理、max_iterations 上限
- test_tools.py：各工具独立测试
- 目标 15-20 条，全部通过

**3. 更新 README**
- 项目定位（跟项目一的对比）
- 系统架构图
- 快速开始
- API 端点文档
- 工具扩展指南（怎么加自定义工具）

**4. 前端打磨**
- 深色主题
- 响应式（移动端也能看）
- 支持中断 Agent 执行

---

## 第 7 天：演示视频 + 简历描述 + 面试准备

### 要做的事

**1. 录制终端演示视频**（1-2 分钟）
- 推荐用 screen.studio 或 OBS
- 场景一：一句话让 Agent 搜资料 + 写报告
- 场景二：Agent 查知识库 + 回答复杂问题

**2. 简历项目描述**

```
项目名：AI 工作流 Agent 引擎 | 独立开发 | 2026.08

技术栈：FastAPI + Anthropic SDK + Chroma + SSE + Tool Use

项目描述：
基于大语言模型的多工具智能体引擎，Agent 能自主理解自然语言任务、
制定执行计划、调度多种工具完成复杂工作流。

核心工作：
· 自研 Agent Loop 循环（Observe→Plan→Act），基于 Anthropic SDK 原生 tool use
· 实现可插拔工具系统：Web Search、File R/W、RAG 检索、Code Exec
· 复用项目一 Chroma 向量库，跨项目知识库共享
· SSE 流式可视化 Agent 完整思考链路（计划→工具调用→结果→总结）
· 容错机制：工具超时重试、LLM 调用指数退避、工具选择回退
```

**3. 面试准备**
- 把 `PROJECT_HIGHLIGHTS.md` 更新，补上项目二的内容
- 准备"两个项目怎么串联"的回答（RAG 知识库 → Agent 工具生态）
- 准备"为什么不用 LangChain"的回答

---

## 两个项目的简历叙事

| | 项目一 | 项目二 |
|------|------|------|
| 项目名 | RAG 知识库问答系统 | AI 工作流 Agent 引擎 |
| 时间 | 2026.07 | 2026.08 |
| 核心能力 | 文档解析→检索→生成 | 自主规划→调度工具→执行 |
| 工具生态 | 3 个 MCP 工具给 Agent 用 | Agent 自己组合工具 |
| 前端效果 | 对话 + 来源展示 | Agent 思考链路可视化 |
| MCP | MCP Server 生产者 | MCP 思想 + SDK tool use |

面试一句话串起来：
> "第一个项目我手搓了 RAG 系统并用 MCP 协议暴露给 Agent 调用。第二个项目我进一步手搓了 Agent 引擎，让 Agent 能自主规划任务、组合多个工具完成复杂工作流。两个项目形成完整的 Agent 工具生态闭环：RAG 提供知识、Agent 负责执行。"

---

## 技术栈清单

| 层 | 技术 | 说明 |
|------|------|------|
| Web 框架 | FastAPI + Uvicorn | 同项目一 |
| LLM 调用 | Anthropic Python SDK | 原生 tool use |
| 流式协议 | SSE | 同项目一，但事件类型更丰富 |
| 向量检索 | Chroma（复用项目一） | 跨项目知识库共享 |
| 工具系统 | 自研可插拔接口 | 类似 MCP 的轻量设计 |
| 网络请求 | aiohttp / requests | 工具网络调用 |
| 前端 | 原生 HTML/CSS/JS | 基于项目一 chat.html 改造 |
| 测试 | pytest | 同项目一 |
