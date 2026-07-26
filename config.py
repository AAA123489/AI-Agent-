"""配置管理 —— 从 .env 加载 API Key 等"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    MODEL: str = "claude-sonnet-5-20251201"
    MAX_TOKENS: int = 4096
    MAX_ITERATIONS: int = 10
    TOOL_TIMEOUT: int = 30  # 秒


config = Config()
