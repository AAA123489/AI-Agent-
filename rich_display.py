"""Rich 终端显示模块 —— Agent 思考过程可视化。

设计原则:
- Rich 输出只在 TTY 环境启用（终端直接运行时）
- 非 TTY 环境（curl / CI / 管道）自动降级为普通 print()
- 不影响 HTTP 响应 —— Rich 只往 stdout 输出
- 全 ASCII 安全，避免 Windows GBK 编码问题
"""

import sys
from rich.console import Console
from rich.panel import Panel
from rich import box

# ── TTY 检测 ──────────────────────────────────────────────
_IS_TTY = sys.stdout.isatty()

# 创建 Rich Console，force_terminal=False 表示「不是终端就别强开」
_console = Console(force_terminal=False, highlight=False)


def set_enabled(enabled: bool):
    """外部开关：允许 AgentLoop 主动关闭 Rich 输出。"""
    global _IS_TTY
    _IS_TTY = enabled and sys.stdout.isatty()


# ── 事件展示函数 ──────────────────────────────────────────

def agent_thinking(step: int, max_steps: int, tools: list[str] | None = None):
    """Agent 每轮推理开始时调用。"""
    if not _IS_TTY:
        print(f"\n--- Step {step}/{max_steps} ---")
        if tools:
            print(f"  Tools: {', '.join(tools)}")
        return

    tools_str = ", ".join(tools) if tools else "none"
    content = f"[bold cyan]Thinking[/bold cyan] (round {step}/{max_steps})"
    content += f"\n[dim]Tools: {tools_str}[/dim]"

    _console.print(
        Panel(content, border_style="cyan", box=box.ROUNDED, padding=(0, 1))
    )


def tool_call(name: str, args: dict):
    """工具被调用时显示。"""
    if not _IS_TTY:
        print(f"  >> {name}({args})")
        return
    _console.print(f"  [yellow]>[/yellow] [bold]{name}[/bold]({args})")


def tool_result(name: str, success: bool, output: str = ""):
    """工具执行完毕后显示结果摘要。"""
    preview = output[:100] + "..." if len(output) > 100 else output
    # 去掉换行，让显示更紧凑
    preview = preview.replace("\n", " ")

    if success:
        if _IS_TTY:
            _console.print(f"  [green]OK[/green] {name} -> {preview}")
        else:
            print(f"  OK {name}: {preview}")
    else:
        if _IS_TTY:
            _console.print(f"  [red]FAIL[/red] {name} -> {preview}")
        else:
            print(f"  FAIL {name}: {preview}")


def agent_response(text: str):
    """Agent 最终回答时显示。"""
    if not _IS_TTY:
        # 非 TTY 模式：响应文本走 HTTP 返回，不需要打印
        return

    _console.print(
        Panel(
            text[:2000],
            title="[bold green]Agent Response[/bold green]",
            border_style="green",
            box=box.ROUNDED,
        )
    )


def agent_error(text: str):
    """Agent 遇到错误时显示。"""
    if not _IS_TTY:
        print(f"\n[ERROR] {text}")
        return
    _console.print(
        Panel(text, title="[bold red]Error[/bold red]", border_style="red", box=box.ROUNDED)
    )
