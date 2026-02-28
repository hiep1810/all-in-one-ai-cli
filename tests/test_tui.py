from aio.agent.executor import AgentExecutor
from aio.config.loader import load_config
from aio.logging.audit import AuditLogger
from aio.memory.session_store import SessionStore
from aio.tools.registry import ToolRegistry
from aio.tui.app import TUIContext, execute_line


def _ctx() -> TUIContext:
    config = load_config()
    registry = ToolRegistry()
    return TUIContext(
        config=config,
        logger=AuditLogger(),
        store=SessionStore(),
        registry=registry,
        executor=AgentExecutor(config, registry),
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
