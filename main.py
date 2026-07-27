"""FastAPI 入口模块。

这个文件是整个 AI Agent 工作流引擎对外暴露的 HTTP 服务入口。
它负责创建 FastAPI 应用实例、配置跨域访问、提供健康检查接口，
并为后续接入前端页面或其他 Web 交互留出扩展点。
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from openai import AsyncOpenAI

from config import config
from agent_loop import AgentLoop
from tools.get_time import get_current_time, TOOL_SCHEMA
from tools.file_tools import write_file, WRITE_FILE_SCHEMA
from tools.rag_search import rag_search, RAG_SEARCH_SCHEMA

# 创建 FastAPI 应用实例。后续所有路由、插件和中间件都会挂载到这个对象上。
app = FastAPI(title="AI Agent Workflow Engine", version="0.1.0")

# 配置 CORS 中间件，允许浏览器前端在开发阶段访问后端接口。
# 这里使用通配符以便快速调试；生产环境建议收敛到具体域名。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """提供一个最小化的服务健康检查接口。

    这个接口通常用于部署后的健康检查、负载均衡探测，
    或者开发期间确认服务是否已经成功启动。
    """
    return {"status": "ok"}


@app.post("/agent")
async def run_agent(payload: dict):
    """接收用户自然语言消息，交给 Agent Loop 执行，返回结果。

    请求体格式：{"message": "现在几点了？"}
    响应格式：{"result": "当前时间是 2026-07-27 20:30:00"}
    """
    user_message = payload.get("message", "")
    if not user_message:
        return {"error": "message 字段不能为空"}

    # 初始化 OpenAI 兼容客户端（DeepSeek）。
    # base_url 指向 DeepSeek API，换成其他 OpenAI 兼容服务一样能用。
    client = AsyncOpenAI(
        api_key=config.ANTHROPIC_API_KEY,
        base_url=config.LLM_BASE_URL,
    )

    # 注册工具：{key: {"handler": fn, "schema": {...}}}
    # schema 格式为 OpenAI function-calling 标准。
    tools = {
        "get_current_time": {
            "handler": get_current_time,
            "schema": TOOL_SCHEMA,
        },
        "write_file": {
            "handler": write_file,
            "schema": WRITE_FILE_SCHEMA,
        },
        "rag_search": {
            "handler": rag_search,
            "schema": RAG_SEARCH_SCHEMA,
        },
    }

    agent = AgentLoop(
        llm_client=client,
        system_prompt=(
            "你是一个智能助手，有一组工具可以帮助你完成任务。\n\n"
            "工具使用规则：\n"
            "1. 用户问时间/日期 → 必须用 get_current_time，不能凭记忆回答\n"
            "2. 用户要保存内容到文件 → 用 write_file\n"
            "3. 用户问知识库里的内容、文档资料、某个主题 → 先用 rag_search 搜索\n"
            "4. 有工具就优先用工具，不要编造信息\n"
            "5. 拿到工具结果后，用自然语言总结给用户"
        ),
        tools=tools,
    )
    result = await agent.run(user_message)
    return {"result": result}


# 第 5 天挂载前端时，可以启用下面这行代码：
# app.mount("/", StaticFiles(directory="static", html=True))
# 这意味着前端静态资源会直接由 FastAPI 提供服务。


if __name__ == "__main__":
    import uvicorn

    # 直接运行脚本时，启动本地开发服务器。
    uvicorn.run(app, host="127.0.0.1", port=8000)
