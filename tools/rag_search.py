"""RAG 知识库检索工具 —— 对接项目一的 Chroma 向量库。

连接项目一已建好的 Chroma 数据库，用同一个向量模型把用户问题
转成向量后检索相关文档片段，返回给 Agent 作为上下文参考。
"""

import os
import asyncio

from chromadb import PersistentClient
from chromadb.utils import embedding_functions

# 项目一的 Chroma 数据库路径（绝对路径，避免工作目录问题）
PROJECT1_CHROMA_PATH = os.path.join(
    os.path.dirname(__file__),      # tools/
    "..",                            # → 项目二根目录
    "..",                            # → vscode-program/
    "AI_Agent_Project",              # → 项目一
    "chroma_db",                     # → 向量库
)

# 跟项目一使用完全一致的 embedding 模型
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# 集合名称，必须跟项目一入库时一致
COLLECTION_NAME = "my_rag_collection"

# 国内镜像加速下载（跟项目一保持一致）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

# 懒加载：首次调用时才加载模型和连接数据库，避免启动时卡住
_chroma_ready = False
_collection = None


def _init_chroma():
    """初始化 Chroma 连接和 embedding 函数（只执行一次）。"""
    global _chroma_ready, _collection

    if _chroma_ready:
        return

    # 连接项目一的持久化向量库
    client = PersistentClient(path=PROJECT1_CHROMA_PATH)

    # 使用跟项目一完全相同的 embedding 模型
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL,
    )

    _collection = client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
    )

    _chroma_ready = True
    total = _collection.count()
    print(f"  📚 RAG 工具已就绪：已连接项目一知识库，共 {total} 条文档片段")


async def rag_search(query: str, top_k: int = 3) -> str:
    """在项目一的知识库中检索相关内容。

    参数:
        query:  要搜索的问题或关键词
        top_k:  返回相关结果的数量，默认 3

    返回:
        格式化后的检索结果文本
    """
    # 首次调用时加载模型和连接数据库
    _init_chroma()

    # chromadb 的 query 是同步的，用线程池避免阻塞事件循环
    results = await asyncio.to_thread(
        _collection.query,
        query_texts=[query],
        n_results=min(top_k, 10),  # 最多 10 条
    )

    # 整理结果
    if not results["ids"] or not results["ids"][0]:
        return f"未找到与「{query}」相关的内容。"

    lines = [f"搜索「{query}」找到 {len(results['ids'][0])} 条结果：\n"]
    for i in range(len(results["ids"][0])):
        doc_id = results["ids"][0][i]
        text = results["documents"][0][i]
        metadata = results["metadatas"][0][i] or {}
        distance = results["distances"][0][i] if results.get("distances") else None

        source = metadata.get("source", "未知来源")
        similarity = f"{(1 - distance) * 100:.0f}%" if distance is not None else "N/A"

        lines.append(f"---")
        lines.append(f"文档 {i + 1} | 来源: {source} | 相关度: {similarity}")
        # 截断过长的文本，保护 Agent 上下文
        preview = text[:300] + "..." if len(text) > 300 else text
        lines.append(preview)

    return "\n".join(lines)


# OpenAI function-calling schema 格式
RAG_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "rag_search",
        "description": (
            "在本地知识库中检索相关内容。当用户问到知识库里的信息、"
            "文档内容、或者需要查资料时使用此工具。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "要搜索的问题或关键词，例如「Python 异步编程」「RAG 原理」",
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回结果数量，默认 3，最多 10",
                },
            },
            "required": ["query"],
        },
    },
}
