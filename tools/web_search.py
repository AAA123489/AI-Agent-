"""Web Search 工具 —— 基于 DuckDuckGo 的免费网页搜索。

不需要 API Key，利用 DuckDuckGo 的 Instant Answer 接口。
用 asyncio.to_thread 包裹同步调用，避免阻塞事件循环。
"""

import asyncio


async def web_search(query: str, max_results: int = 5) -> str:
    """搜索互联网，返回相关网页的标题、链接和摘要。

    参数:
        query:       搜索关键词
        max_results: 返回结果数量，默认 5，最多 10

    返回:
        格式化后的搜索结果文本
    """
    # 限制最大结果数，避免上下文爆炸
    max_results = min(max_results, 10)

    # 在线程池中执行同步搜索（duckduckgo_search 库是同步的）
    try:
        results = await asyncio.to_thread(_do_search, query, max_results)
    except ImportError:
        return (
            "Web Search 工具未安装。请运行: pip install ddgs"
        )
    except asyncio.TimeoutError:
        return (
            "搜索请求超时。可能原因：网络不稳定或搜索服务暂时不可用，"
            "请稍后重试。"
        )
    except Exception as e:
        error_msg = str(e)
        if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
            return "搜索请求超时，网络连接不稳定，请稍后重试。"
        return f"搜索失败: {error_msg}"

    if not results:
        return f"未找到与「{query}」相关的搜索结果。"

    # 格式化输出
    lines = [f"搜索「{query}」找到 {len(results)} 条结果:\n"]
    for i, item in enumerate(results, 1):
        title = item.get("title", "无标题")
        href = item.get("href", "")
        body = item.get("body", "")

        # 截断过长的摘要
        if len(body) > 200:
            body = body[:200] + "..."

        lines.append(f"{i}. {title}")
        if href:
            lines.append(f"   URL: {href}")
        lines.append(f"   {body}")
        lines.append("")

    return "\n".join(lines)


def _do_search(query: str, max_results: int) -> list[dict]:
    """同步搜索函数，在线程池中执行。"""
    from ddgs import DDGS

    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
    return results


# OpenAI function-calling schema 格式
WEB_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "搜索互联网，返回相关网页的标题、链接和摘要。"
            "当需要查找最新信息、实时数据、或知识库中没有的内容时使用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，例如「Python asyncio 教程」「2026 年 AI 趋势」",
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回结果数量，默认 5，最多 10",
                },
            },
            "required": ["query"],
        },
    },
}
