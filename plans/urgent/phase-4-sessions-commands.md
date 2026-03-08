# Phase 4 — Session Management + Custom Commands

## What This Phase Does (Big Picture)

Two problems:

1. **Sessions are lost.** You close the TUI, your conversation is gone. The current `SessionStore` only appends messages — there's no way to list, resume, or delete sessions.
2. **No shortcuts.** If you run the same prompt every day ("review my staged changes"), you have to type it out each time.

This phase adds:
- **Full session management:** save, list, resume, delete, and fork conversations
- **Custom commands:** reusable prompt templates stored as `.md` files

> **Junior tip:** Sessions = saved game files. Custom commands = keyboard macros.

## Inspired By

| Tool | How They Do It |
|:--|:--|
| **Claude Code** | `--resume <tag>`, `-c` (continue last), session forking |
| **Gemini CLI** | `/chat save/resume/list/delete` with per-project scoping |
| **OpenCode** | SQLite-backed sessions with Ctrl+N (new), Ctrl+X (switch), MD custom commands with `$ARG` placeholders |

## Design Patterns Used

### 1. CRUD (Create, Read, Update, Delete)

- **One-Line ELI5:** The four basic operations you can do on any data: create it, read it, update it, delete it.
- **Why Here:** Sessions are data. Users need to create (save), read (resume), update (append), and delete them. CRUD is the simplest mental model.
- **Real Analogy:** Like contacts on your phone — you add, view, edit, and delete contacts. Same operations, different data.

### 2. Template Pattern (for custom commands)

- **One-Line ELI5:** A text with placeholders that get filled in at runtime.
- **Why Here:** A custom command like `"Review changes by $AUTHOR in $DIRECTORY"` has placeholders. When the user runs it, they provide values (`AUTHOR=hiep`, `DIRECTORY=src/`), and the placeholders get replaced.
- **Real Analogy:** Like a form letter — "Dear $NAME, your order #$ORDER is ready." Same template, different values each time.

### 3. Discovery Pattern (for commands)

- **One-Line ELI5:** Instead of hardcoding a list, the system *discovers* items by scanning a directory.
- **Why Here:** Custom commands are `.md` files in a folder. Instead of registering each one manually, we scan `.aio/commands/` and auto-discover them. Add a file = add a command.
- **Real Analogy:** Like a jukebox — it doesn't have a hardcoded song list. It scans the CD tray and shows whatever CDs are loaded.

## Files to Create/Modify

```
src/aio/
├── memory/
│   └── session_store.py   ← MODIFY (add list/load/delete/fork)
├── config/
│   └── commands.py        ← NEW (command discovery + expansion)
├── tui/
│   ├── app.py             ← MODIFY (\session + \command commands)
│   └── command_palette.py ← MODIFY (include custom commands)
└── cli.py                 ← MODIFY (--resume flag)
```

---

## Detailed Implementation

### [MODIFY] `src/aio/memory/session_store.py`

**Add 4 new methods** to `SessionStore`:

```python
def list_sessions(self) -> list[dict]:
    """
    Scans the sessions directory and returns metadata:
    [{"name": "debug-auth", "messages": 24, "last_modified": "2026-03-07T15:00:00"}]
    
    Uses Path.stat() for file metadata.
    Sorts by last_modified descending (newest first).
    """

def load(self, session: str) -> list[dict]:
    """
    Reads all messages from a session file.
    Each line is a JSON object (JSONL format).
    Returns a list of message dicts.
    
    Why JSONL reading is simple:
    - Each line is independent — no need to parse the whole file
    - If one line is corrupt, the rest still work
    """

def delete(self, session: str) -> bool:
    """Deletes a session file. Returns True if deleted, False if not found."""

def fork(self, source: str, target: str) -> Path:
    """
    Copies a session to a new name.
    
    Why copy instead of move:
    - The original session is preserved
    - The user can "branch" from a checkpoint
    - Like git branch — the original stays, you get a new copy
    """
```

### [NEW] `src/aio/config/commands.py`

```python
@dataclass
class CommandDef:
    name: str           # e.g., "review-pr"
    scope: str          # "user" or "project"
    template: str       # The markdown content with $ARG placeholders
    source_path: Path   # Where the .md file lives

def discover_commands(project_root: Path) -> dict[str, CommandDef]:
    """
    Scans two directories for .md files:
    1. ~/.aio/commands/  → prefixed as "user:filename" 
    2. .aio/commands/    → prefixed as "project:filename"
    
    Subdirectories are supported:
    .aio/commands/git/review.md → "project:git:review"
    """

def expand_command(cmd: CommandDef, args: dict[str, str]) -> str:
    """
    Replaces $ARG_NAME placeholders with provided values.
    
    Uses regex: \$([A-Z][A-Z0-9_]*)
    
    Example:
    Template: "Review commits by $AUTHOR in $DIR"
    Args: {"AUTHOR": "hiep", "DIR": "src/"}
    Result: "Review commits by hiep in src/"
    
    Raises ValueError if a required placeholder has no value.
    """
```

> **Junior tip:** The regex `\$([A-Z][A-Z0-9_]*)` means: match a `$` sign followed by an uppercase letter, then zero or more uppercase letters, digits, or underscores. So `$FILE_PATH` matches but `$lowercase` or `$123` don't. This prevents accidental matches with normal text.

### [MODIFY] `src/aio/tui/app.py`

New commands in `_execute_line_sync`:

| Command | Action |
|:--|:--|
| `\session list` | Show all saved sessions with message count and date |
| `\session save <name>` | Save current conversation to a named session |
| `\session resume <name>` | Load a session's messages and continue the conversation |
| `\session delete <name>` | Delete a session |
| `\session fork <source> <target>` | Copy a session to a new name |
| `\compact` | Summarize current context via LLM, replace history with summary |
| `\command <name> [KEY=VALUE ...]` | Run a custom command |

### [MODIFY] `src/aio/tui/command_palette.py`

Add discovered custom commands to `self.options` list so they appear in Ctrl+K search.

---

## Tests

### [NEW] `tests/test_session.py`

```python
def test_list_sessions_returns_metadata(tmp_path):
    # Create 2 .jsonl files with some messages → verify list returns 2 items

def test_load_session_reads_all_messages(tmp_path):
    # Append 3 messages → load → verify 3 dicts returned

def test_delete_session_removes_file(tmp_path):
    # Create session → delete → verify file gone

def test_fork_session_copies_data(tmp_path):
    # Create session A → fork to B → verify B has same content, A still exists
```

### [NEW] `tests/test_commands.py`

```python
def test_discover_project_commands(tmp_path):
    # Create .aio/commands/greet.md → verify discovered as "project:greet"

def test_discover_nested_commands(tmp_path):
    # Create .aio/commands/git/review.md → verify "project:git:review"

def test_expand_command_replaces_args():
    # Template with $NAME, expand with NAME=Hiep → verify "Hiep" in result

def test_expand_command_missing_arg_raises():
    # Template with $REQUIRED, expand with {} → ValueError
```

## How to Verify Manually

1. `aio tui` → chat for a bit → `\session save test1` → exit → reopen → `\session resume test1` → conversation continues
2. `\session list` → see saved sessions
3. Create `.aio/commands/review.md` with: `Review these staged changes:\n\nRUN git diff --staged`
4. `\command project:review` → AI receives the expanded prompt
