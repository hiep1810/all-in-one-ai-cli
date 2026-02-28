from pathlib import Path

from aio.agent.executor import AgentExecutor
from aio.config.schema import Config
from aio.config.loader import load_config
from aio.logging.audit import AuditLogger
from aio.memory.session_store import SessionStore
from aio.tools.registry import ToolRegistry
from aio.tui.app import (
    APPROVAL_REQUIRED_PREFIX,
    CLEAR_SIGNAL,
    TUIContext,
    _inject_approve_flag,
    _requires_approval,
    clear_to_line_end,
    clear_to_line_start,
    complete_input,
    complete_slash_command,
    delete_forward,
    delete_prev_word,
    delete_backspace,
    execute_line,
    history_next,
    history_prev,
    insert_text,
    reset_input_state,
    reverse_search_prev,
    suggest_input,
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


def test_complete_input_tool_name():
    out = complete_input("\\tool fs.se", ["fs.search", "fs.read"])
    assert out == "\\tool fs.search "


def test_complete_input_config_key():
    out = complete_input("\\config set model_b", [])
    assert out == "\\config set model_base_url "


def test_complete_input_config_value_hint():
    out = complete_input("\\config set safety_level st", [])
    assert out == "\\config set safety_level strict "


def test_suggest_input_for_root_command():
    out = suggest_input("\\co", [])
    assert "config" in out


def test_suggest_input_for_tool_name():
    out = suggest_input("\\tool fs.", ["fs.search", "fs.read", "shell.exec"])
    assert "fs.search" in out
    assert "fs.read" in out


def test_suggest_input_for_config_value():
    out = suggest_input("\\config set safety_level ", [])
    assert "strict" in out


def test_history_prev_and_next_with_draft_restore():
    history = ["first", "second", "third"]
    idx = None
    draft = ""
    buf = "typing now"

    idx, draft, buf = history_prev(history, idx, draft, buf)
    assert (idx, draft, buf) == (2, "typing now", "third")
    idx, draft, buf = history_prev(history, idx, draft, buf)
    assert (idx, buf) == (1, "second")
    idx, draft, buf = history_next(history, idx, draft, buf)
    assert (idx, buf) == (2, "third")
    idx, draft, buf = history_next(history, idx, draft, buf)
    assert idx is None
    assert buf == "typing now"


def test_history_prev_on_empty_history_is_noop():
    idx, draft, buf = history_prev([], None, "", "abc")
    assert idx is None
    assert draft == ""
    assert buf == "abc"


def test_reverse_search_prev_with_query():
    history = ["\\help", "hello world", "\\tool fs.search root=. query=TODO"]
    idx, value = reverse_search_prev(history, "tool", None)
    assert idx == 2
    assert value == "\\tool fs.search root=. query=TODO"


def test_reverse_search_prev_repeated_from_older_index():
    history = ["alpha", "beta alpha", "gamma alpha"]
    idx, value = reverse_search_prev(history, "alpha", None)
    assert (idx, value) == (2, "gamma alpha")
    idx2, value2 = reverse_search_prev(history, "alpha", idx - 1)
    assert (idx2, value2) == (1, "beta alpha")


def test_reverse_search_prev_on_empty_history():
    idx, value = reverse_search_prev([], "x", None)
    assert idx is None
    assert value is None


def test_reset_input_state():
    pending, reverse_idx, history_idx, draft = reset_input_state("draft text")
    assert pending is None
    assert reverse_idx is None
    assert history_idx is None
    assert draft == "draft text"


def test_reset_input_state_empty_draft():
    pending, reverse_idx, history_idx, draft = reset_input_state("")
    assert pending is None
    assert reverse_idx is None
    assert history_idx is None
    assert draft == ""


def test_insert_text_at_cursor():
    updated, cursor = insert_text("helo", 3, "l")
    assert updated == "hello"
    assert cursor == 4


def test_delete_backspace_at_cursor():
    updated, cursor = delete_backspace("hello", 3)
    assert updated == "helo"
    assert cursor == 2


def test_clear_to_line_start_with_cursor():
    updated, cursor = clear_to_line_start("hello world", 6)
    assert updated == "world"
    assert cursor == 0


def test_clear_to_line_end_with_cursor():
    updated, cursor = clear_to_line_end("hello world", 5)
    assert updated == "hello"
    assert cursor == 5


def test_delete_forward_at_cursor():
    updated, cursor = delete_forward("hello", 1)
    assert updated == "hllo"
    assert cursor == 1


def test_delete_prev_word():
    updated, cursor = delete_prev_word("say hello world", 10)
    assert updated == "say world"
    assert cursor == 4


def test_tui_tool_risky_requires_approve_in_confirm_mode():
    ctx = _ctx(Config(safety_level="confirm"))
    out = execute_line(ctx, "\\tool shell.exec cmd=echo_hi")
    assert "Approval required" in out


def test_tui_tool_risky_runs_with_approve_flag():
    ctx = _ctx(Config(safety_level="confirm"))
    out = execute_line(ctx, "\\tool shell.exec cmd=echo_hi --approve-risky")
    assert "echo_hi" in out


def test_tui_tool_validation_error_is_returned():
    ctx = _ctx(Config(safety_level="off"))
    out = execute_line(ctx, "\\tool fs.search root=.")
    assert "Missing required args" in out


def test_tui_agent_risky_requires_approve_in_confirm_mode():
    ctx = _ctx(Config(safety_level="confirm"))
    out = execute_line(ctx, "\\agent hello")
    assert out.startswith(APPROVAL_REQUIRED_PREFIX)


def test_requires_approval_detection():
    assert _requires_approval("Approval required for risky tool: shell.exec")
    assert not _requires_approval("other message")


def test_inject_approve_flag():
    assert _inject_approve_flag("\\tool shell.exec cmd=echo_hi") == (
        "\\tool shell.exec cmd=echo_hi --approve-risky"
    )
    assert _inject_approve_flag("\\tool shell.exec --approve-risky") == (
        "\\tool shell.exec --approve-risky"
    )
