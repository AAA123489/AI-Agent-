"""工具独立测试 —— 验证每个工具的输入输出行为。"""

import os

import pytest

from tools.get_time import get_current_time
from tools.file_tools import write_file, read_file, list_files
from tools.web_search import web_search
from tools.weather import get_weather


# ═══════════════════════════════════════════════════════════════
# get_current_time
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_current_time_format():
    """返回格式 YYYY-MM-DD HH:MM:SS 的字符串。"""
    result = await get_current_time()
    assert isinstance(result, str)
    assert len(result) == 19  # "2026-07-29 12:00:00"
    # 验证各部分可解析
    parts = result.split(" ")
    assert len(parts) == 2
    date_parts = parts[0].split("-")
    time_parts = parts[1].split(":")
    assert len(date_parts) == 3
    assert len(time_parts) == 3
    # 年份范围合理
    assert 2020 <= int(date_parts[0]) <= 2099


# ═══════════════════════════════════════════════════════════════
# file_tools: write_file / read_file / list_files
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_write_and_read_file(tmp_path):
    """写文件 → 读回内容一致。"""
    filepath = tmp_path / "test.txt"
    result = await write_file(str(filepath), "Hello pytest")
    assert "写入成功" in result
    assert os.path.exists(filepath)

    content = await read_file(str(filepath))
    assert "Hello pytest" in content


@pytest.mark.asyncio
async def test_read_file_not_found():
    """读不存在的文件返回错误提示。"""
    result = await read_file("/nonexistent/path/xyz.nope")
    assert "文件不存在" in result


@pytest.mark.asyncio
async def test_write_file_creates_directory(tmp_path):
    """写文件时自动创建不存在的目录。"""
    filepath = tmp_path / "new_dir" / "sub" / "out.txt"
    result = await write_file(str(filepath), "nested content")
    assert "写入成功" in result
    assert os.path.exists(filepath)


@pytest.mark.asyncio
async def test_list_files(tmp_path):
    """列目录输出包含已知文件名。"""
    (tmp_path / "a.txt").touch()
    (tmp_path / "b.txt").touch()
    (tmp_path / "subdir").mkdir()

    result = await list_files(str(tmp_path))
    assert "a.txt" in result
    assert "b.txt" in result
    assert "subdir" in result


@pytest.mark.asyncio
async def test_list_files_nonexistent_directory():
    """列不存在的目录返回错误。"""
    result = await list_files("/nonexistent/dir/xyz")
    assert "不存在" in result


# ═══════════════════════════════════════════════════════════════
# web_search (需要网络)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_web_search_returns_string():
    """搜索返回字符串（网络不可用时 skip）。"""
    try:
        result = await web_search("Python programming", max_results=1)
    except Exception as e:
        msg = str(e).lower()
        if "timeout" in msg or "网络" in msg or "timed out" in msg:
            pytest.skip(f"Network unavailable: {e}")
        raise

    assert isinstance(result, str)
    assert len(result) > 0


# ═══════════════════════════════════════════════════════════════
# get_weather (需要网络 + API Key)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_weather_returns_string():
    """天气查询返回字符串（网络不可用时 skip）。"""
    try:
        result = await get_weather("北京")
    except Exception as e:
        msg = str(e).lower()
        if "timeout" in msg or "connection" in msg or "dns" in msg:
            pytest.skip(f"Network unavailable: {e}")
        raise

    assert isinstance(result, str)
    assert len(result) > 0
