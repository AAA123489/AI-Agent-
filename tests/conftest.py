"""pytest 共享 fixture —— mock LLM 客户端、测试工具、辅助函数。"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from openai import AsyncOpenAI


# ═══════════════════════════════════════════════════════════════
# 辅助函数：构建 mock LLM 响应
# ═══════════════════════════════════════════════════════════════

def make_text_response(content: str) -> MagicMock:
    """构建 finish_reason='stop' 的 mock 响应。"""
    choice = MagicMock()
    choice.finish_reason = "stop"
    choice.message = MagicMock()
    choice.message.content = content
    choice.message.tool_calls = None

    resp = MagicMock()
    resp.choices = [choice]
    return resp


def make_tool_calls_response(tool_calls_data: list[dict]) -> MagicMock:
    """构建 finish_reason='tool_calls' 的 mock 响应。

    tool_calls_data 格式:
        [{"name": "echo", "arguments": '{"message":"hello"}'}]
    """
    tool_calls = []
    model_dump_calls = []
    for i, tc in enumerate(tool_calls_data):
        call = MagicMock()
        call.id = f"call_{i}"
        call.function = MagicMock()
        call.function.name = tc["name"]
        call.function.arguments = tc["arguments"]
        tool_calls.append(call)

        model_dump_calls.append({
            "id": f"call_{i}",
            "function": {
                "name": tc["name"],
                "arguments": tc["arguments"],
            },
        })

    choice = MagicMock()
    choice.finish_reason = "tool_calls"
    choice.message = MagicMock()
    choice.message.content = None
    choice.message.tool_calls = tool_calls
    choice.message.model_dump.return_value = {
        "role": "assistant",
        "tool_calls": model_dump_calls,
    }

    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_llm_client():
    """返回 AsyncMock 包装的假 LLM 客户端。"""
    client = MagicMock(spec=AsyncOpenAI)
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock()
    return client


@pytest.fixture
def echo_tool():
    """一个简单的 echo 工具，用于测试 Agent Loop。"""
    async def echo_handler(message: str) -> str:
        return f"Echo: {message}"

    return {
        "echo": {
            "handler": echo_handler,
            "schema": {
                "type": "function",
                "function": {
                    "name": "echo",
                    "description": "Echoes back the message",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "The message to echo",
                            }
                        },
                        "required": ["message"],
                    },
                },
            },
        }
    }


@pytest.fixture
def agent_loop_factory(mock_llm_client):
    """工厂函数：用 mock client 创建 AgentLoop 实例。"""
    def _create(tools=None, max_iterations=5):
        from agent_loop import AgentLoop

        return AgentLoop(
            llm_client=mock_llm_client,
            system_prompt="You are a helpful assistant. Use tools when needed.",
            tools=tools or {},
            max_iterations=max_iterations,
            use_rich=False,
        )

    return _create
