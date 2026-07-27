"""第 1 天假工具 —— get_current_time

验证 Agent Loop 能正确：LLM 识别工具 → 调用工具 → 接收结果 → 继续推理
"""

from datetime import datetime


async def get_current_time() -> str:
    """返回当前日期和时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# OpenAI function-calling schema 格式（DeepSeek 兼容）
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": "返回当前的日期和时间，格式为 YYYY-MM-DD HH:MM:SS",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}
