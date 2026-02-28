from pathlib import Path

from aio.mcp.server import _handle_tool_call, _resolve_path


def test_resolve_path_within_root(tmp_path: Path):
    root = tmp_path
    p = _resolve_path(root, "a.txt")
    assert p == (root / "a.txt").resolve()


def test_resolve_path_outside_root_raises(tmp_path: Path):
    root = tmp_path
    try:
        _resolve_path(root, "../outside.txt")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "outside allowed root" in str(exc)


def test_handle_tool_call_read_markdown(tmp_path: Path):
    md = tmp_path / "README.md"
    md.write_text("# Hello\n", encoding="utf-8")
    result = _handle_tool_call(tmp_path, "read_markdown", {"path": "README.md"})
    text = result["content"][0]["text"]
    assert "# Hello" in text


def test_handle_tool_call_list_files(tmp_path: Path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.md").write_text("b", encoding="utf-8")
    result = _handle_tool_call(tmp_path, "list_files", {"glob": "*.txt"})
    text = result["content"][0]["text"]
    assert "a.txt" in text
    assert "b.md" not in text
