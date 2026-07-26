"""Agent 核心循环 —— Observe → Plan → Act

整个项目的心脏。流程：

    用户输入
      ↓
    Agent Loop 开始 ──→ LLM 分析任务，决定下一步
        ↑                    ↓
        │            LLM 返回：调用工具 OR 最终答案
        │                    ↓
        └── 工具执行结果 ←── 如需要，执行工具函数

    如果 LLM 说"任务完成" → 跳出循环，返回结果
"""

import json
from typing import Any, Callable, Awaitable
from dataclasses import dataclass, field


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_name: str
    success: bool
    output: str


@dataclass
class AgentLoop:
    """Agent 核心循环

    Args:
        system_prompt: 系统 Prompt
        tools: 可用工具列表（每个工具是 name + handler 的字典）
        max_iterations: 最大循环轮次（防止死循环 + API 费用兜底）
    """
    system_prompt: str
    tools: dict = field(default_factory=dict)
    max_iterations: int = 10

    async def run(self, user_input: str) -> str:
        """执行 Agent 循环，返回最终答案

        Args:
            user_input: 用户自然语言输入

        Returns:
            Agent 的最终文本回复
        """
        # TODO: 第 1 天 —— 实现循环
        raise NotImplementedError("第 1 天实现")
