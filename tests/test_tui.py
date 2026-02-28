from pathlib import Path

from aio.agent.executor import AgentExecutor
from aio.config.loader import load_config
from aio.logging.audit import AuditLogger
from aio.memory.session_store import SessionStore
from aio.tools.registry import ToolRegistry
from aio.tui.app import CLEAR_SIGNAL, TUIContext, execute_line


def _ctx() -> TUIContext:
    config = load_config()
    registry = ToolRegistry()
    return TUIContext(
        config=config,
        logger=AuditLogger(),
        store=SessionStore(),
        registry=registry,
        executor=AgentExecutor(config, registry),
        command_history=[],
        last_response="",
    )


def test_tui_tools_command_lists_core_tools():
    out = execute_line(_ctx(), "\\tools")
    assert "fs.search" in out
    assert "shell.exec" in out


def test_tui_help_command():
    out = execute_line(_ctx(), "\\help")
    assert "Commands:" in out


def test_tui_config_show_command():
    out = execute_line(_ctx(), "\\config show")
    assert "model_provider" in out


def test_tui_plain_text_is_chat():
    out = execute_line(_ctx(), "hello")
    assert "hello" in out


def test_tui_history_command():
    ctx = _ctx()
    execute_line(ctx, "hello")
    execute_line(ctx, "\\tools")
    out = execute_line(ctx, "\\history 2")
    assert "hello" in out
    assert "\\tools" in out


def test_tui_clear_command():
    out = execute_line(_ctx(), "\\clear")
    assert out == CLEAR_SIGNAL


def test_tui_save_command(tmp_path: Path):
    ctx = _ctx()
    execute_line(ctx, "hello world")
    output_file = tmp_path / "export.txt"
    out = execute_line(ctx, f"\\save {output_file}")
    assert "Saved transcript" in out
    assert output_file.exists()
    assert "hello world" in output_file.read_text(encoding="utf-8")
