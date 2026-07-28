"""文件操作工具集 —— write_file / read_file / list_files"""

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
# ── read_file ────────────────────────────────────────────

async def read_file(path: str) -> str:
    """读取本地文本文件的内容（仅 UTF-8 编码）。

    参数:
        path: 要读取的文件路径

    返回:
        文件内容，或错误描述
    """
    # 安全检查：拒绝读取敏感系统文件
    if not os.path.exists(path):
        return f"文件不存在: {path}"

    if not os.path.isfile(path):
        return f"路径不是文件: {path}"

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except PermissionError:
        return f"没有权限读取文件: {path}"
    except UnicodeDecodeError:
        return f"文件不是有效的 UTF-8 文本，无法读取: {path}"
    except Exception as e:
        return f"读取文件失败: {str(e)}"

    # 防止超大文件撑爆 Agent 上下文
    MAX_CHARS = 10_000
    if len(content) > MAX_CHARS:
        content = content[:MAX_CHARS]
        truncate_note = f"\n\n... (文件过大，仅显示前 {MAX_CHARS} 字符)"
    else:
        truncate_note = ""

    return f"文件 {path} 的内容 ({len(content)} 字符):\n\n{content}{truncate_note}"


# ── list_files ───────────────────────────────────────────

async def list_files(directory: str = ".") -> str:
    """列出指定目录下的文件和子目录。

    参数:
        directory: 目录路径，默认为当前工作目录

    返回:
        格式化的目录列表
    """
    if not os.path.exists(directory):
        return f"目录不存在: {directory}"

    if not os.path.isdir(directory):
        return f"路径不是目录: {directory}"

    try:
        entries = os.listdir(directory)
    except PermissionError:
        return f"没有权限访问目录: {directory}"
    except Exception as e:
        return f"列出目录失败: {str(e)}"

    if not entries:
        return f"目录 {directory} 是空的。"

    # 排序，目录排前面
    entries.sort(key=lambda name: (not os.path.isdir(os.path.join(directory, name)), name.lower()))

    MAX_ENTRIES = 200
    total = len(entries)
    if total > MAX_ENTRIES:
        entries = entries[:MAX_ENTRIES]
        truncate_note = f"\n... (目录过大，仅显示前 {MAX_ENTRIES} 项，共 {total} 项)"
    else:
        truncate_note = ""

    lines = [f"目录 {directory} 的内容 ({total} 项):\n"]
    for name in entries:
        full_path = os.path.join(directory, name)
        marker = "/" if os.path.isdir(full_path) else ""
        lines.append(f"  {name}{marker}")

    return "\n".join(lines) + truncate_note


# ── Schemas ──────────────────────────────────────────────

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

READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "读取本地文本文件的内容。仅支持 UTF-8 编码的文本文件。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要读取的文件路径，例如 data/notes.txt",
                },
            },
            "required": ["path"],
        },
    },
}

LIST_FILES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_files",
        "description": "列出指定目录下的文件和子目录。目录以 / 结尾标识。",
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "要列出的目录路径，例如 tools/ 或 . (当前目录)",
                },
            },
            "required": [],
        },
    },
}
