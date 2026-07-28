"""FastAPI 入口模块。

这个文件是整个 AI Agent 工作流引擎对外暴露的 HTTP 服务入口。
它负责创建 FastAPI 应用实例、配置跨域访问、提供健康检查接口，
以及 Agent 推理的 SSE 流式端点。
"""

import json
import re
import sys
from dataclasses import fields

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from openai import AsyncOpenAI

from config import config
from agent_loop import AgentLoop
from tools.get_time import get_current_time, TOOL_SCHEMA
from tools.file_tools import (
    write_file, WRITE_FILE_SCHEMA,
    read_file, READ_FILE_SCHEMA,
    list_files, LIST_FILES_SCHEMA,
)
from tools.rag_search import rag_search, RAG_SEARCH_SCHEMA
from tools.web_search import web_search, WEB_SEARCH_SCHEMA
from tools.weather import get_weather, GET_WEATHER_SCHEMA

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
    """Agent 推理端点 —— SSE 流式输出事件。

    请求体格式：{"message": "现在几点了？"}
    响应格式：text/event-stream（SSE），逐事件推送

    事件类型：thinking / tool_call / tool_result / text / done / error

    也兼容旧版 JSON 一把梭模式：请求头 Accept: application/json 时
    改为返回 {"result": "..."}（向后兼容 curl 测试）。
    """
    user_message = payload.get("message", "")
    if not user_message:
        raise HTTPException(status_code=400, detail="message 字段不能为空")

    # 初始化 OpenAI 兼容客户端（DeepSeek）。
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
        "read_file": {
            "handler": read_file,
            "schema": READ_FILE_SCHEMA,
        },
        "list_files": {
            "handler": list_files,
            "schema": LIST_FILES_SCHEMA,
        },
        "rag_search": {
            "handler": rag_search,
            "schema": RAG_SEARCH_SCHEMA,
        },
        "web_search": {
            "handler": web_search,
            "schema": WEB_SEARCH_SCHEMA,
        },
        "get_weather": {
            "handler": get_weather,
            "schema": GET_WEATHER_SCHEMA,
        },
    }

    agent = AgentLoop(
        llm_client=client,
        system_prompt=(
            "你是一个智能助手，有一组工具可以帮助你完成任务。\n\n"
            "工具使用规则：\n"
            "1. 用户问时间/日期 → 必须用 get_current_time，不能凭记忆回答\n"
            "2. 用户要保存内容到文件 → 用 write_file\n"
            "3. 用户要读取文件内容 → 用 read_file\n"
            "4. 用户要查看目录结构/有哪些文件 → 用 list_files\n"
            "5. 用户问知识库里的内容、文档资料、某个主题 → 先用 rag_search 搜索\n"
            "6. 用户问最新信息、实时数据、或知识库中没有的内容 → 用 web_search\n"
            "7. 用户问天气 → 用 get_weather\n"
            "8. 有工具就优先用工具，不要编造信息\n"
            "8. 拿到工具结果后，用自然语言总结给用户"
        ),
        tools=tools,
        use_rich=False,  # HTTP 模式关闭 Rich，走 SSE
    )

    async def event_stream():
        """SSE 事件生成器：把 Agent 事件转为 data: {json}\n\n 格式。"""
        try:
            async for event in agent.run_stream(user_message):
                # 事件对象 → {"type": "thinking", "step": 1, ...}
                # 例: ThinkingEvent → "thinking", ToolCallEvent → "tool_call"
                raw_name = event.__class__.__name__.replace("Event", "")
                event_type = re.sub(r'(?<!^)(?=[A-Z])', '_', raw_name).lower()
                data: dict = {"type": event_type}
                for f in fields(event):
                    data[f.name] = getattr(event, f.name)
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

            # 正常结束标记
            yield "data: [DONE]\n\n"

        except Exception as e:
            error_data = json.dumps(
                {"type": "error", "message": str(e)},
                ensure_ascii=False,
            )
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# 挂载前端静态文件。
# 注意：必须放在所有 API 路由之后，否则会吞掉 /agent 和 /health。
app.mount("/", StaticFiles(directory="static", html=True))


if __name__ == "__main__":
    import uvicorn

    # 直接运行脚本时，启动本地开发服务器。
    uvicorn.run(app, host="127.0.0.1", port=8000)
