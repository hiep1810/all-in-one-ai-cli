"""
tests/test_context.py — Tests for the hierarchical context loader.

Pattern tested: Hierarchical Config Merge + Append-only log
"""
from pathlib import Path

from aio.memory.context import append_memory, load_project_context


def test_load_context_missing_file_returns_empty(tmp_path: Path) -> None:
    # No .aio/context.md exists at all — should return empty string
    result = load_project_context(project_root=tmp_path)
    assert result == ""


def test_load_context_reads_project_file(tmp_path: Path) -> None:
    # Create project-level .aio/context.md
    aio_dir = tmp_path / ".aio"
    aio_dir.mkdir()
    (aio_dir / "context.md").write_text("Always use Python 3.11.\n", encoding="utf-8")

    result = load_project_context(project_root=tmp_path)

    assert "Always use Python 3.11." in result


def test_load_context_includes_section_header(tmp_path: Path) -> None:
    # Each section should have a descriptive header so the AI knows the source
    aio_dir = tmp_path / ".aio"
    aio_dir.mkdir()
    (aio_dir / "context.md").write_text("Use Flask.\n", encoding="utf-8")

    result = load_project_context(project_root=tmp_path)

    assert "Project context from" in result
    assert "Use Flask." in result


def test_load_context_empty_file_returns_empty(tmp_path: Path) -> None:
    # An empty context file should be silently skipped
    aio_dir = tmp_path / ".aio"
    aio_dir.mkdir()
    (aio_dir / "context.md").write_text("   \n", encoding="utf-8")

    result = load_project_context(project_root=tmp_path)

    assert result == ""


def test_append_memory_creates_file_and_appends(tmp_path: Path) -> None:
    # first call → creates the file
    path = append_memory("use tabs not spaces", project_root=tmp_path)
    assert path.exists()
    assert "use tabs not spaces" in path.read_text(encoding="utf-8")


def test_append_memory_appends_multiple_facts(tmp_path: Path) -> None:
    # two calls → both facts appear in the file, in order
    append_memory("use tabs not spaces", project_root=tmp_path)
    append_memory("always add type hints", project_root=tmp_path)

    content = (tmp_path / ".aio" / "context.md").read_text(encoding="utf-8")

    assert "use tabs not spaces" in content
    assert "always add type hints" in content
    # tabs fact should appear before type hints fact
    assert content.index("use tabs") < content.index("always add type hints")


def test_append_memory_strips_whitespace(tmp_path: Path) -> None:
    # Leading/trailing whitespace in the fact should be stripped before saving
    append_memory("   tidy fact   ", project_root=tmp_path)
    content = (tmp_path / ".aio" / "context.md").read_text(encoding="utf-8")
    assert "tidy fact\n" in content
