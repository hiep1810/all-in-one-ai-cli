from aio.tools.registry import ToolRegistry


def test_registry_has_core_tools():
    tools = ToolRegistry().list_tools()
    assert "fs.search" in tools
    assert "shell.exec" in tools
