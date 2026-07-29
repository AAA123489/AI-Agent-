"""Agent Loop 核心测试 —— mock LLM 客户端，验证事件流和循环逻辑。"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_loop import (
    AgentLoop,
    ThinkingEvent,
    ToolCallEvent,
    ToolResultEvent,
    TextEvent,
    DoneEvent,
    ErrorEvent,
)
from config import config
from tests.conftest import make_text_response, make_tool_calls_response


# ═══════════════════════════════════════════════════════════════
# run_stream() 事件流测试
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_direct_text_response_no_tools(agent_loop_factory, mock_llm_client):
    """Agent 没有工具可用，LLM 直接返回文本。"""
    mock_llm_client.chat.completions.create.return_value = make_text_response("Hello.")

    agent = agent_loop_factory(tools={})
    events = [e async for e in agent.run_stream("hi")]

    assert len(events) == 3
    assert isinstance(events[0], ThinkingEvent)
    assert events[0].step == 1
    assert isinstance(events[1], TextEvent)
    assert events[1].content == "Hello."
    assert isinstance(events[2], DoneEvent)


@pytest.mark.asyncio
async def test_single_tool_call_then_text(agent_loop_factory, mock_llm_client, echo_tool):
    """第 1 轮调工具，第 2 轮返回文本 — 标准 happy path。"""
    mock_llm_client.chat.completions.create.side_effect = [
        make_tool_calls_response([{"name": "echo", "arguments": '{"message":"hi"}'}]),
        make_text_response("All done."),
    ]

    agent = agent_loop_factory(tools=echo_tool)
    events = [e async for e in agent.run_stream("hello")]

    # 第 1 轮: thinking → tool_call → tool_result
    # 第 2 轮: thinking → text → done
    assert len(events) == 6

    assert isinstance(events[0], ThinkingEvent)  # step 1
    assert events[0].step == 1
    assert isinstance(events[1], ToolCallEvent)
    assert events[1].tool == "echo"
    assert events[1].args == {"message": "hi"}
    assert isinstance(events[2], ToolResultEvent)
    assert events[2].success is True
    assert events[2].tool == "echo"

    assert isinstance(events[3], ThinkingEvent)  # step 2
    assert events[3].step == 2
    assert isinstance(events[4], TextEvent)
    assert events[4].content == "All done."
    assert isinstance(events[5], DoneEvent)


@pytest.mark.asyncio
async def test_multi_tool_chain(agent_loop_factory, mock_llm_client, echo_tool):
    """连续两轮都调工具，第三轮才返回文本。"""
    mock_llm_client.chat.completions.create.side_effect = [
        make_tool_calls_response([{"name": "echo", "arguments": '{"message":"a"}'}]),
        make_tool_calls_response([{"name": "echo", "arguments": '{"message":"b"}'}]),
        make_text_response("Done."),
    ]

    agent = agent_loop_factory(tools=echo_tool)
    events = [e async for e in agent.run_stream("test")]

    # 3 Thinking + 2 ToolCall + 2 ToolResult + 1 Text + 1 Done = 9
    thinking_events = [e for e in events if isinstance(e, ThinkingEvent)]
    tool_call_events = [e for e in events if isinstance(e, ToolCallEvent)]
    tool_result_events = [e for e in events if isinstance(e, ToolResultEvent)]
    text_events = [e for e in events if isinstance(e, TextEvent)]
    done_events = [e for e in events if isinstance(e, DoneEvent)]

    assert len(thinking_events) == 3
    assert len(tool_call_events) == 2
    assert len(tool_result_events) == 2
    assert len(text_events) == 1
    assert len(done_events) == 1


# ═══════════════════════════════════════════════════════════════
# run() 向后兼容测试
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_run_returns_final_text(agent_loop_factory, mock_llm_client, echo_tool):
    """run() 应返回最终文本字符串。"""
    mock_llm_client.chat.completions.create.side_effect = [
        make_tool_calls_response([{"name": "echo", "arguments": '{"message":"x"}'}]),
        make_text_response("Final answer."),
    ]

    agent = agent_loop_factory(tools=echo_tool)
    result = await agent.run("test")
    assert result == "Final answer."


# ═══════════════════════════════════════════════════════════════
# 错误处理测试
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_api_error_yields_error_event(agent_loop_factory, mock_llm_client):
    """LLM API 抛异常时，yield ErrorEvent 并终止。"""
    mock_llm_client.chat.completions.create.side_effect = Exception("API down")

    agent = agent_loop_factory()
    events = [e async for e in agent.run_stream("test")]

    assert len(events) == 2
    assert isinstance(events[0], ThinkingEvent)
    assert isinstance(events[1], ErrorEvent)
    assert "API down" in events[1].message


@pytest.mark.asyncio
async def test_max_iterations_reached(agent_loop_factory, mock_llm_client, echo_tool):
    """LLM 持续请求调工具，达到最大轮数后 ErrorEvent 终止。"""
    # 每次调用都返回 tool_calls
    mock_llm_client.chat.completions.create.side_effect = [
        make_tool_calls_response([{"name": "echo", "arguments": '{"message":"loop"}'}])
        for _ in range(10)
    ]

    agent = agent_loop_factory(tools=echo_tool, max_iterations=3)
    events = [e async for e in agent.run_stream("test")]

    thinking_events = [e for e in events if isinstance(e, ThinkingEvent)]
    error_events = [e for e in events if isinstance(e, ErrorEvent)]

    assert len(thinking_events) == 3  # 在第 3 轮后达到上限
    assert len(error_events) == 1
    assert "最大循环次数" in error_events[0].message


@pytest.mark.asyncio
async def test_unknown_tool_keyerror(agent_loop_factory, mock_llm_client, echo_tool):
    """LLM 请求不存在的工具 → ToolResultEvent(success=False)。"""
    mock_llm_client.chat.completions.create.side_effect = [
        # 第一轮: 请求不存在的工具
        make_tool_calls_response([{"name": "not_registered", "arguments": "{}"}]),
        # 第二轮: 看到错误后 LLM 回复文本
        make_text_response("Tool failed, I'll answer directly."),
    ]

    agent = agent_loop_factory(tools=echo_tool)
    events = [e async for e in agent.run_stream("test")]

    tool_results = [e for e in events if isinstance(e, ToolResultEvent)]
    assert len(tool_results) == 1
    assert tool_results[0].success is False
    assert "不存在" in tool_results[0].output

    # 仍能正常结束
    text_events = [e for e in events if isinstance(e, TextEvent)]
    assert len(text_events) == 1


@pytest.mark.asyncio
async def test_tool_timeout(agent_loop_factory, mock_llm_client):
    """工具执行超时 → ToolResultEvent(success=False)。"""
    async def slow_tool() -> str:
        await asyncio.sleep(999)
        return "never"

    slow_tools = {
        "slow": {
            "handler": slow_tool,
            "schema": {
                "type": "function",
                "function": {
                    "name": "slow",
                    "description": "A very slow tool",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
        }
    }

    mock_llm_client.chat.completions.create.side_effect = [
        make_tool_calls_response([{"name": "slow", "arguments": "{}"}]),
        make_text_response("Timed out, moving on."),
    ]

    # 临时把超时改为 0.1 秒
    original_timeout = config.TOOL_TIMEOUT
    config.TOOL_TIMEOUT = 0.1

    try:
        agent = agent_loop_factory(tools=slow_tools)
        events = [e async for e in agent.run_stream("test")]

        tool_results = [e for e in events if isinstance(e, ToolResultEvent)]
        assert len(tool_results) == 1
        assert tool_results[0].success is False
        assert "超时" in tool_results[0].output
    finally:
        config.TOOL_TIMEOUT = original_timeout


@pytest.mark.asyncio
async def test_tool_execution_error(agent_loop_factory, mock_llm_client):
    """工具 handler 抛 RuntimeError → ToolResultEvent(success=False)。"""
    async def broken_tool() -> str:
        raise RuntimeError("Something went wrong")

    broken_tools = {
        "broken": {
            "handler": broken_tool,
            "schema": {
                "type": "function",
                "function": {
                    "name": "broken",
                    "description": "Always errors",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
        }
    }

    mock_llm_client.chat.completions.create.side_effect = [
        make_tool_calls_response([{"name": "broken", "arguments": "{}"}]),
        make_text_response("Handled the error."),
    ]

    agent = agent_loop_factory(tools=broken_tools)
    events = [e async for e in agent.run_stream("test")]

    tool_results = [e for e in events if isinstance(e, ToolResultEvent)]
    assert len(tool_results) == 1
    assert tool_results[0].success is False
    assert "Something went wrong" in tool_results[0].output


@pytest.mark.asyncio
async def test_json_decode_fallback(agent_loop_factory, mock_llm_client, echo_tool):
    """LLM 返回非法 JSON 参数 → tool_args 回退为 {}。"""
    mock_llm_client.chat.completions.create.side_effect = [
        make_tool_calls_response([{"name": "echo", "arguments": "not valid json!!!"}]),
        make_text_response("Done despite bad JSON."),
    ]

    agent = agent_loop_factory(tools=echo_tool)
    events = [e async for e in agent.run_stream("test")]

    # tool_args 应该是 {}
    tool_call = next(e for e in events if isinstance(e, ToolCallEvent))
    assert tool_call.args == {}

    # echo handler 会收到 message=""（默认值），然后因为 required=["message"] 这取决于工具实现
    # 这里主要是验证 JSON decode 异常被捕获，不会让整个循环崩溃
    tool_result = next(e for e in events if isinstance(e, ToolResultEvent))
    # 工具还是执行了（参数为 {} 虽然缺了 message，但 handler 会收到默认值）
    # Key point: 没有因为 JSONDecodeError 崩溃
    assert tool_result is not None


@pytest.mark.asyncio
async def test_empty_user_input_runs(agent_loop_factory, mock_llm_client):
    """空输入也能正常走 Agent Loop（LLM 自己会处理）。"""
    mock_llm_client.chat.completions.create.return_value = make_text_response("Empty input received.")

    agent = agent_loop_factory()
    events = [e async for e in agent.run_stream("")]

    text_events = [e for e in events if isinstance(e, TextEvent)]
    assert len(text_events) == 1
    assert "Empty input" in text_events[0].content
