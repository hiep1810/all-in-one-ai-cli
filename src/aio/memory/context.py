"""
memory/context.py — Project context file loader.

Pattern: Hierarchical Config Merge
  ELI5: Settings from multiple levels (global → project) are stacked
        together so the AI gets all your instructions at once.
  Why here: A user may have personal preferences globally (~/.aio/context.md)
            AND project-specific rules (.aio/context.md). Both matter.
  Analogy: Dress codes — company-wide rules + your team's extra rules both apply.
"""
from __future__ import annotations

from pathlib import Path


# The filename is the same at every level so it's easy to remember.
CONTEXT_FILENAME = "context.md"
AIO_DIR = ".aio"


def load_project_context(project_root: Path | None = None) -> str:
    """
    Discover and concatenate context files from (lowest → highest priority):
      1. ~/.aio/context.md   — global, personal developer preferences
      2. <project>/.aio/context.md — project-level, shared by team

    Each found file is included with a small header so the AI knows
    where each section came from.

    Returns the combined text, or empty string if no files exist.

    Why we concatenate instead of override:
      Both levels contain useful info. Global says "always use type hints",
      project says "this is a Flask app". The AI needs both.
    """
    # Why we use a list instead of a string: Strings are immutable in Python, so doing
    # `string += new_string` creates a new string object every time. Appending to a list
    # and then calling `"".join()` at the end is much more memory efficient.
    sections: list[str] = []

    # Level 1: global context in the user's home directory
    # Why pathlib (Path) instead of os.path: pathlib provides an object-oriented
    # approach to paths that works consistently across Windows and Posix, avoiding
    # manual string concatenation for slashes (e.g. `Path.home() / dir` vs `dir + "/"`)
    global_ctx = Path.home() / AIO_DIR / CONTEXT_FILENAME
    if global_ctx.exists() and global_ctx.is_file():
        text = global_ctx.read_text(encoding="utf-8").strip()
        if text:
            sections.append(f"[Global context from {global_ctx}]\n{text}")

    # Level 2: project-level context
    root = project_root or Path.cwd()
    project_ctx = root / AIO_DIR / CONTEXT_FILENAME
    if project_ctx.exists() and project_ctx.is_file():
        text = project_ctx.read_text(encoding="utf-8").strip()
        if text:
            sections.append(f"[Project context from {project_ctx}]\n{text}")

    # Join sections with a blank line separator so the AI can tell them apart
    return "\n\n".join(sections)


def append_memory(fact: str, project_root: Path | None = None) -> Path:
    """
    Append a single fact to the project's .aio/context.md file.

    Pattern: Append-only log
      ELI5: Instead of rewriting the whole file, we just add to the end.
      Why here: Safe and fast — no risk of accidentally erasing existing context.
      Analogy: A sticky-note pad — you add new notes, never erase old ones.

    Creates the file (and .aio/ directory) if they don't exist yet.
    Returns the path to the context file.
    """
    root = project_root or Path.cwd()
    ctx_path = root / AIO_DIR / CONTEXT_FILENAME

    # Ensure .aio/ directory exists before writing
    ctx_path.parent.mkdir(parents=True, exist_ok=True)

    # Append the fact followed by a newline.
    # We use "a" mode (append) — never overwrites existing content.
    with ctx_path.open("a", encoding="utf-8") as f:
        f.write(fact.strip() + "\n")

    return ctx_path
