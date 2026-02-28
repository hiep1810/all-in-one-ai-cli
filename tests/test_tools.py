from aio.tools.registry import ToolRegistry
from aio.utils.errors import ToolValidationError


def test_registry_has_core_tools():
    tools = ToolRegistry().list_tools()
    assert "fs.search" in tools
    assert "shell.exec" in tools


def test_registry_validates_missing_required_args():
    registry = ToolRegistry()
    try:
        registry.run("fs.search", root=".")
        assert False, "Expected ToolValidationError"
    except ToolValidationError as exc:
        assert "Missing required args" in str(exc)


def test_registry_validates_unknown_args():
    registry = ToolRegistry()
    try:
        registry.run("shell.exec", cmd="echo hi", extra="x")
        assert False, "Expected ToolValidationError"
    except ToolValidationError as exc:
        assert "Unknown args" in str(exc)


def test_registry_validates_arg_types():
    registry = ToolRegistry()
    try:
        registry.run("shell.exec", cmd=123)
        assert False, "Expected ToolValidationError"
    except ToolValidationError as exc:
        assert "Invalid type" in str(exc)
