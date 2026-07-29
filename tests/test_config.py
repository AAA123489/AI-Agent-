"""配置管理测试 —— 验证 config 加载和默认值。"""

import os

import pytest


def test_config_defaults():
    """Config 实例的默认值正确。"""
    from config import config

    assert config.MODEL == "deepseek-chat"
    assert config.MAX_TOKENS == 4096
    assert config.MAX_ITERATIONS == 10
    assert config.TOOL_TIMEOUT == 30
    assert config.LLM_BASE_URL == "https://api.deepseek.com"


def test_config_api_key_is_string():
    """API Key 字段存在且为字符串类型。"""
    from config import config

    assert isinstance(config.ANTHROPIC_API_KEY, str)


def test_config_numeric_types():
    """数值型配置项确实是 int 类型。"""
    from config import config

    assert isinstance(config.MAX_TOKENS, int)
    assert isinstance(config.MAX_ITERATIONS, int)
    assert isinstance(config.TOOL_TIMEOUT, int)
