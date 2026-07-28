import json
import asyncio
from typing import Any, AsyncGenerator, Dict, List
from dataclasses import dataclass, field

from openai import AsyncOpenAI

from config import config
from rich_display import (
    agent_thinking,
    tool_call as rich_tool_call,
    tool_result as rich_tool_result,
    agent_response as rich_agent_response,
    agent_error as rich_agent_error,
    set_enabled as rich_set_enabled,
)


# ═══════════════════════════════════════════════════════════════════
# Agent 事件类型 —— 连接 Agent Loop 和表现层（SSE / Rich）
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ThinkingEvent:
    """每轮推理开始时触发。"""
    step: int
    max_steps: int
    tools: List[str]


@dataclass
class ToolCallEvent:
    """Agent 决定调用某个工具。"""
    tool: str
    args: Dict[str, Any]


@dataclass
class ToolResultEvent:
    """工具执行完毕（成功或失败）。"""
    tool: str
    success: bool
    output: str


@dataclass
class TextEvent:
    """Agent 最终回复文本。"""
    content: str


@dataclass
class DoneEvent:
    """任务正常完成。"""
    pass


@dataclass
class ErrorEvent:
    """发生错误（API 故障 / 超时 / 达到上限）。"""
    message: str


# 所有事件类型的联合（用于类型标注）
AgentEvent = ThinkingEvent | ToolCallEvent | ToolResultEvent | TextEvent | DoneEvent | ErrorEvent


@dataclass
class ToolResult:
    """封装一次工具调用的结果，便于统一处理和后续回传给模型。"""

    tool_name: str
    success: bool
    output: str


@dataclass
class AgentLoop:
    """Agent 核心循环 —— 基于 OpenAI 兼容 SDK（DeepSeek 等）。

    流程：用户输入 → LLM 分析 → 调工具 / 给出答案 → 循环 → 返回结果

    支持两种调用方式：
    - run(): 返回最终文本（向后兼容 curl）
    - run_stream(): async generator，yield 事件对象（SSE / Rich 消费）
    """

    llm_client: AsyncOpenAI
    system_prompt: str
    tools: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    max_iterations: int = 10
    model: str = config.MODEL
    max_tokens: int = config.MAX_TOKENS
    use_rich: bool = True  # True = 终端 Rich 输出，False = 纯 print

    def __post_init__(self):
        """初始化 Rich 显示开关。"""
        rich_set_enabled(self.use_rich)

    # ── 公开 API ──────────────────────────────────────────────

    async def run(self, user_input: str) -> str:
        """执行一次 Agent 对话，返回最终结果文本。

        向后兼容：curl / 旧代码仍然可以拿到 {"result": "..."} 一把梭响应。
        内部调用 run_stream() 收集事件，同时驱动 Rich 终端显示。
        """
        final_text = ""
        async for event in self.run_stream(user_input):
            # 把事件流转成 Rich 终端输出（TTY 自动检测）
            if isinstance(event, ThinkingEvent):
                agent_thinking(event.step, event.max_steps, event.tools)
            elif isinstance(event, ToolCallEvent):
                rich_tool_call(event.tool, event.args)
            elif isinstance(event, ToolResultEvent):
                rich_tool_result(event.tool, event.success, event.output)
            elif isinstance(event, TextEvent):
                rich_agent_response(event.content)
                final_text = event.content
            elif isinstance(event, ErrorEvent):
                rich_agent_error(event.message)
        return final_text

    async def run_stream(self, user_input: str) -> AsyncGenerator[AgentEvent, None]:
        """SSE 流式版本 —— 逐事件 yield，供 SSE 端点或 Rich 消费者使用。"""

        # OpenAI 把 system prompt 作为一条消息放在对话最前面。
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input},
        ]

        # 提取所有已注册工具的 schema（OpenAI function-calling 格式）。
        tools_schema = [
            t["schema"] for t in self.tools.values()
        ] if self.tools else None

        # ═══════════════════════════════════════════════════
        # Agent 主循环
        # ═══════════════════════════════════════════════════
        for step in range(self.max_iterations):
            tool_names = (
                [t["function"]["name"] for t in tools_schema]
                if tools_schema else []
            )

            # → 事件: 本轮思考开始
            yield ThinkingEvent(
                step=step + 1,
                max_steps=self.max_iterations,
                tools=tool_names,
            )

            # 向模型发起一次推理请求。
            create_kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": messages,
                "temperature": 0,
            }
            if tools_schema:
                create_kwargs["tools"] = tools_schema
                # 第 1 轮强制调工具，确保 DeepSeek 不走捷径
                # 后续轮次改回 auto，让模型拿到结果后能正常结束
                if step == 0:
                    create_kwargs["tool_choice"] = "required"
                else:
                    create_kwargs["tool_choice"] = "auto"

            # LLM API 调用异常处理
            try:
                response = await self.llm_client.chat.completions.create(**create_kwargs)
            except Exception as e:
                yield ErrorEvent(message=f"LLM API 调用失败: {str(e)}")
                return

            choice = response.choices[0]
            finish_reason = choice.finish_reason

            # finish_reason == "stop" → 任务完成
            if finish_reason == "stop":
                final_text = choice.message.content or ""
                yield TextEvent(content=final_text)
                yield DoneEvent()
                return

            # 模型请求调用工具
            if finish_reason == "tool_calls" or (
                finish_reason != "stop" and choice.message.tool_calls
            ):
                # 先把包含 tool_calls 的助手消息加入历史。
                messages.append(choice.message.model_dump())

                tool_result_messages = []

                for tool_call in choice.message.tool_calls:
                    tool_name = tool_call.function.name

                    # OpenAI 协议中 arguments 是 JSON 字符串，需要手动解析。
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}

                    # → 事件: 准备调工具
                    yield ToolCallEvent(tool=tool_name, args=tool_args)

                    # 执行注册过的工具处理器（带超时保护）。
                    try:
                        handler = self.tools[tool_name]["handler"]
                        output = await asyncio.wait_for(
                            handler(**tool_args),
                            timeout=config.TOOL_TIMEOUT,
                        )
                        result = ToolResult(
                            tool_name=tool_name,
                            success=True,
                            output=str(output),
                        )
                    except asyncio.TimeoutError:
                        result = ToolResult(
                            tool_name=tool_name,
                            success=False,
                            output=(
                                f"工具 '{tool_name}' 执行超时"
                                f"（{config.TOOL_TIMEOUT}秒），已取消。"
                            ),
                        )
                    except KeyError:
                        result = ToolResult(
                            tool_name=tool_name,
                            success=False,
                            output=(
                                f"工具 '{tool_name}' 不存在。"
                                f"可用工具：{list(self.tools.keys())}"
                            ),
                        )
                    except Exception as e:
                        result = ToolResult(
                            tool_name=tool_name,
                            success=False,
                            output=f"工具 '{tool_name}' 执行错误：{str(e)}",
                        )

                    # → 事件: 工具结果
                    yield ToolResultEvent(
                        tool=tool_name,
                        success=result.success,
                        output=result.output,
                    )

                    # 把工具结果组织成 OpenAI 的 tool 消息格式。
                    tool_result_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result.output,
                    })

                # 将所有工具执行结果追加到消息历史。
                messages.extend(tool_result_messages)
                continue

            # 兜底：遇到意外的 finish_reason（如 length 截断）。
            yield ErrorEvent(
                message=f"意外 finish_reason: {finish_reason} (step {step + 1})"
            )
            return

        # 达到最大循环次数仍未结束。
        yield ErrorEvent(
            message=f"达到最大循环次数（{self.max_iterations}轮），任务未能完成。"
        )
