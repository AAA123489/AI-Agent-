"""配置管理模块。

这个文件负责从环境变量中读取项目运行所需的配置项，并提供一个统一的配置对象。
通过把配置集中到这里，可以避免在各个模块里散落硬编码参数，也更利于后续扩展。
"""

import os
from dotenv import load_dotenv

# 在导入配置时，主动加载项目根目录下的 .env 文件。
# 这样开发者就可以把 API Key、模型名等敏感或常变配置放到环境文件中。
load_dotenv()


class Config:
    """统一的运行配置类。

    这里把系统中常用的配置项都定义成类属性，方便在其它模块中直接访问。
    """

    # 从环境变量读取 LLM 的 API Key；如果没有配置，保持为空字符串。
    # 这一步可以避免程序在启动时因为缺少密钥而直接报错。
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # LLM 服务的基础地址。支持任意 OpenAI 兼容的 API 服务。
    # DeepSeek 默认地址：https://api.deepseek.com
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")

    # 默认使用的 LLM 模型名称。
    # DeepSeek 推荐：deepseek-chat（V3）或 deepseek-reasoner（R1）
    MODEL: str = os.getenv("MODEL", "deepseek-chat")

    # 单次模型生成允许使用的最大 token 数。
    # 数值越大，回答越丰富，但也会带来更高的成本和延迟。
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4096"))

    # Agent 循环允许执行的最大轮数。
    # 用于防止模型不断调用工具或陷入重复推理导致资源浪费。
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "10"))

    # 工具执行超时时间，单位为秒。
    # 如果某个工具长时间未返回，会被视为失败并由 Agent 处理。
    TOOL_TIMEOUT: int = int(os.getenv("TOOL_TIMEOUT", "30"))


# 创建一个全局配置实例，方便整个项目中任何模块直接引用。
config = Config()
