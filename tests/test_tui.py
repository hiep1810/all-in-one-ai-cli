from pathlib import Path

from aio.agent.executor import AgentExecutor
from aio.config.schema import Config
from aio.config.loader import load_config
from aio.logging.audit import AuditLogger
from aio.memory.session_store import SessionStore
from aio.tools.registry import ToolRegistry
from aio.tui.app import (
    CLEAR_SIGNAL,
    TUIContext,
    complete_slash_command,
    execute_line,
    iter_stream_chunks,
)


def _ctx(config: Config | None = None) -> TUIContext:
    config = config or load_config()
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


def test_complete_slash_command_unique_match():
    assert complete_slash_command("\\wor") == "\\workflow "


def test_complete_slash_command_shared_prefix():
    assert complete_slash_command("\\to") == "\\tool"


def test_complete_slash_command_noop_for_plain_text():
    assert complete_slash_command("hello") == "hello"


def test_stream_chunks_default_size():
    chunks = iter_stream_chunks("abcdefghijk")
    assert chunks == ["abcdefgh", "ijk"]


def test_stream_chunks_custom_size():
    chunks = iter_stream_chunks("abcdef", chunk_size=2)
    assert chunks == ["ab", "cd", "ef"]


def test_tui_tool_risky_requires_approve_in_confirm_mode():
    ctx = _ctx(Config(safety_level="confirm"))
    out = execute_line(ctx, "\\tool shell.exec cmd=echo_hi")
    assert "Approval required" in out


def test_tui_tool_risky_runs_with_approve_flag():
    ctx = _ctx(Config(safety_level="confirm"))
    out = execute_line(ctx, "\\tool shell.exec cmd=echo_hi --approve-risky")
    assert "echo_hi" in out
