import json
from typing import Any, Dict, List
from dataclasses import dataclass, field

from openai import AsyncOpenAI

from config import config


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
    """

    llm_client: AsyncOpenAI
    system_prompt: str
    tools: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    max_iterations: int = 10
    model: str = config.MODEL
    max_tokens: int = config.MAX_TOKENS

    async def run(self, user_input: str) -> str:
        """执行一次 Agent 对话，返回最终结果文本。"""

        # OpenAI 把 system prompt 作为一条消息放在对话最前面。
        # 这样模型在一开始就能理解自己的角色和行为约束。
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input},
        ]

        # 提取所有已注册工具的 schema（OpenAI function-calling 格式）。
        # 如果没有工具，传 None 表示本轮不支持工具调用。
        tools_schema = [
            t["schema"] for t in self.tools.values()
        ] if self.tools else None

        # ═══════════════════════════════════════════════
        # Agent 主循环
        # ═══════════════════════════════════════════════
        for step in range(self.max_iterations):
            print(f"\n{'=' * 50}")
            print(f"[Step {step + 1}/{self.max_iterations}] LLM 思考中...")
            if tools_schema:
                print(f"  可用工具: {[t['function']['name'] for t in tools_schema]}")

            # 向模型发起一次推理请求。
            # 模型会依据当前对话上下文，决定是直接回答还是调用工具。
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

            response = await self.llm_client.chat.completions.create(**create_kwargs)

            choice = response.choices[0]
            finish_reason = choice.finish_reason

            # finish_reason == "stop" 表示模型认为任务已完成，直接回复文本。
            if finish_reason == "stop":
                final_text = choice.message.content or ""
                print(f"[Step {step + 1}] ✅ 任务完成")
                return final_text

            # 如果模型请求调用工具，就执行工具并把结果回传。
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

                    print(f"  🔧 调用工具: {tool_name}({tool_args})")

                    # 执行注册过的工具处理器。
                    try:
                        handler = self.tools[tool_name]["handler"]
                        output = await handler(**tool_args)
                        result = ToolResult(
                            tool_name=tool_name,
                            success=True,
                            output=str(output),
                        )
                        print(f"  ✅ 工具返回: {output}")
                    except KeyError:
                        result = ToolResult(
                            tool_name=tool_name,
                            success=False,
                            output=f"工具 '{tool_name}' 不存在。可用工具：{list(self.tools.keys())}",
                        )
                        print(f"  ❌ {result.output}")
                    except Exception as e:
                        result = ToolResult(
                            tool_name=tool_name,
                            success=False,
                            output=f"执行错误：{str(e)}",
                        )
                        print(f"  ❌ {result.output}")

                    # 把工具结果组织成 OpenAI 的 tool 消息格式。
                    tool_result_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result.output,
                    })

                # 将所有工具执行结果追加到消息历史。
                # 下一轮模型会看到"刚才工具执行了什么，返回了什么结果"。
                messages.extend(tool_result_messages)
                continue

            # 兜底：遇到意外的 finish_reason（如 length 截断）。
            print(f"[Step {step + 1}] ⚠️ 意外 finish_reason: {finish_reason}")
            return choice.message.content or ""

        # 达到最大循环次数仍未结束，可能是任务太复杂或模型陷入循环。
        return f"⚠️ 达到最大循环次数（{self.max_iterations}轮），任务未能完成。"
