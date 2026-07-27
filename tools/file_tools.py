"""文件操作工具集 —— write_file / read_file 等"""

import os


async def write_file(path: str, content: str) -> str:
    """把文本内容写入指定文件。如果目录不存在，自动创建。"""
    dir_path = os.path.dirname(path)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    file_size = os.path.getsize(path)
    return f"写入成功。文件: {path}，大小: {file_size} 字节"


# OpenAI function-calling schema 格式
WRITE_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "将文本内容写入本地文件。如果目录不存在会自动创建。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要写入的文件路径，例如 output/report.md",
                },
                "content": {
                    "type": "string",
                    "description": "要写入文件的文本内容",
                },
            },
            "required": ["path", "content"],
        },
    },
}
