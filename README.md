# AI Agent Workflow Engine

> Natural-language-driven multi-tool orchestration system.
> Built from scratch -- no LangChain, no CrewAI, just the OpenAI SDK and a custom Agent Loop.

---

## Architecture

```
  Browser (agent.html)          POST /agent (SSE)         AgentLoop.run_stream()
  ┌──────────────────┐         ┌──────────────┐         ┌─────────────────────┐
  │  Sidebar         │         │  FastAPI      │         │  ThinkingEvent      │
  │  - Tool list     │──SSE──▶│  /health       │────────▶│  ToolCallEvent       │
  │  - Quick tags    │         │  POST /agent   │         │  ToolResultEvent     │
  │                  │         │  Static files  │         │  TextEvent           │
  │  Chat area       │◀───────│  CORS          │         │  DoneEvent           │
  │  - Timeline      │         └──────────────┘         │  ErrorEvent          │
  │  - Bubbles       │                                   └──────────┬──────────┘
  └──────────────────┘                                              │
                                                         ┌──────────┴──────────┐
                                                         │  7 Plugin Tools      │
                                                         │  ┌────────────────┐  │
                                                         │  │ get_current_time│  │
                                                         │  │ write_file      │  │
                                                         │  │ read_file       │  │
                                                         │  │ list_files      │  │
                                                         │  │ rag_search  ────┼──▶ ChromaDB (Project 1)
                                                         │  │ web_search  ────┼──▶ DuckDuckGo
                                                         │  │ get_weather ────┼──▶ Amap API
                                                         │  └────────────────┘  │
                                                         └──────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10+
- A DeepSeek API key (or any OpenAI-compatible service)

### Setup

```bash
# 1. Clone
git clone https://github.com/AAA123489/AI-Agent-.git
cd AI-Agent-

# 2. Virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY=sk-your-deepseek-key

# 5. Run
python main.py
# Open http://127.0.0.1:8000
```

## API

### `GET /health`

Health check. Returns `{"status": "ok"}`.

### `POST /agent`

Agent inference with SSE streaming.

**Request:**
```json
{"message": "What time is it? Save to time.txt"}
```

**Response:** `text/event-stream` -- 6 event types streamed as `data: {...}\n\n`:

| Event | Fields | When |
|-------|--------|------|
| `thinking` | `step`, `max_steps`, `tools` | Each reasoning round begins |
| `tool_call` | `tool`, `args` | Agent invokes a tool |
| `tool_result` | `tool`, `success`, `output` | Tool execution completes |
| `text` | `content` | Final answer text |
| `done` | — | Task completed normally |
| `error` | `message` | Error occurred |

End-of-stream marker: `data: [DONE]\n\n`

## Built-in Tools (7)

| Tool | File | Description |
|------|------|-------------|
| `get_current_time` | `tools/get_time.py` | Returns current date and time |
| `write_file` | `tools/file_tools.py` | Write text to a file (auto-creates directories) |
| `read_file` | `tools/file_tools.py` | Read text file contents (UTF-8, max 10K chars) |
| `list_files` | `tools/file_tools.py` | List directory contents (dirs first, max 200) |
| `rag_search` | `tools/rag_search.py` | Search Project 1's ChromaDB knowledge base |
| `web_search` | `tools/web_search.py` | DuckDuckGo free web search (no API key) |
| `get_weather` | `tools/weather.py` | Amap (Gaode) weather -- real-time + 4-day forecast |

## Adding a New Tool

### 1. Create the tool file

`tools/my_tool.py`:
```python
async def my_tool(param: str) -> str:
    return f"Result: {param}"

MY_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "my_tool",
        "description": "What this tool does",
        "parameters": {
            "type": "object",
            "properties": {
                "param": {
                    "type": "string",
                    "description": "Parameter description"
                }
            },
            "required": ["param"]
        }
    }
}
```

### 2. Register in `main.py`

```python
from tools.my_tool import my_tool, MY_TOOL_SCHEMA
tools["my_tool"] = {"handler": my_tool, "schema": MY_TOOL_SCHEMA}
```

### 3. Update the system prompt in `main.py`

Add a usage hint so the model knows when to use your tool.

## Configuration (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Your LLM API key (name kept for compatibility) |
| `LLM_BASE_URL` | `https://api.deepseek.com` | OpenAI-compatible API endpoint |
| `MODEL` | `deepseek-chat` | Model name |
| `MAX_TOKENS` | `4096` | Max tokens per generation |
| `MAX_ITERATIONS` | `10` | Max Agent reasoning rounds |
| `TOOL_TIMEOUT` | `30` | Tool execution timeout (seconds) |

## Project Structure

```
.
├── main.py                  # FastAPI entry, SSE endpoint, tool registration
├── agent_loop.py            # Agent core loop (event-driven, async generator)
├── config.py                # Configuration from .env
├── prompts.py               # System prompt template
├── rich_display.py          # Terminal visualization (Rich, TTY-aware)
├── tools/
│   ├── get_time.py          # Time tool
│   ├── file_tools.py        # write_file / read_file / list_files
│   ├── rag_search.py        # RAG knowledge base retrieval
│   ├── web_search.py        # DuckDuckGo web search
│   └── weather.py           # Amap weather API
├── static/
│   ├── agent.html           # Single-page frontend (SSE consumer, timeline UI)
│   └── index.html           # Redirect to agent.html
├── tests/
│   ├── conftest.py          # Shared fixtures, mock helpers
│   ├── test_agent_loop.py   # Core loop tests (11 tests)
│   ├── test_tools.py        # Tool tests (8 tests)
│   └── test_config.py       # Config tests (3 tests)
├── requirements.txt
├── pytest.ini
└── README.md
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web framework | FastAPI + Uvicorn |
| LLM client | OpenAI SDK (DeepSeek compatible) |
| Streaming | Server-Sent Events (SSE) |
| Vector DB | ChromaDB (reused from Project 1) |
| Embeddings | sentence-transformers (MiniLM-L12-v2) |
| Web search | DuckDuckGo via `ddgs` |
| Weather | Amap Open Platform API |
| Frontend | Vanilla HTML/CSS/JS (single file) |
| Terminal UI | Rich |
| Testing | pytest + pytest-asyncio (22 tests) |

## Relationship to Project 1

| | Project 1: RAG QA | Project 2: Agent Engine |
|---|---|---|
| Core | Document parsing → retrieval → generation | Autonomous planning → tool orchestration → execution |
| LLM role | Answer from retrieved context | Decide which tools, in what order |
| Tools | 3 MCP tools (exposed externally) | 7 built-in tools (orchestrated internally) |
| Streaming | SSE + source citations | SSE + full thinking trace (timeline) |
| Shared | — | ChromaDB vector store from Project 1 |

> "Project 1 built a RAG system and exposed it via MCP. Project 2 built an Agent engine that autonomously plans, schedules, and combines multiple tools -- including the RAG knowledge base from Project 1. Together they form a complete Agent tool ecosystem: RAG provides knowledge, the Agent handles execution."

## Development

```bash
# Run tests
pytest tests/ -v

# Start dev server
python main.py

# Check API
curl http://127.0.0.1:8000/health
```

## License

MIT
