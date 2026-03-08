# Phase 2 — @ File Injection + New Tools

## What This Phase Does (Big Picture)

Right now, if you want the AI to read a file, you have to manually copy-paste it or use `\tool fs.read path=file.py`. This phase adds two major features:

1. **@ File Injection** — type `explain @src/main.py` and the file's contents are automatically inserted into your prompt
2. **3 New Tools** — `web.fetch`, `web.search`, and `patch.apply` to give the AI abilities it's currently missing

> **Junior tip:** Think of `@file.py` like tagging someone on social media — you're saying "include this file in the conversation."

## Inspired By

| Tool | How They Do It |
|:--|:--|
| **Gemini CLI** | `@path/to/file` injects file content into prompt, supports directories too |
| **OpenCode** | Built-in `fetch` tool for URLs, `edit` tool for diff-based file editing |
| **Claude Code** | Web fetch via bash, file editing via `replace` tool |

## Design Patterns Used

### 1. Preprocessor / Template Expansion

- **One-Line ELI5:** Before the prompt reaches the AI, we scan it for special tokens and replace them with actual content.
- **Why Here:** The user types `explain @README.md`, we replace `@README.md` with the file contents *before* sending to the LLM. The LLM sees the full file content, not the `@` token.
- **Real Analogy:** Like mail merge — you write "Dear $NAME" and the system replaces `$NAME` with "Hiep" before sending.

### 2. Adapter / Wrapper (for web tools)

- **One-Line ELI5:** A thin layer that translates between your code and an external system's interface.
- **Why Here:** Python's `urllib` is powerful but verbose. Our `web.fetch()` adapter wraps it into a simple `fetch(url) → text` call, handling encoding, timeouts, and HTML-to-text conversion.
- **Real Analogy:** Like a power adapter — the wall socket (urllib) and your device (our tool) speak different shapes, the adapter makes them compatible.

### 3. Pure Functions (for tools)

- **One-Line ELI5:** A function that takes input, returns output, and doesn't change anything else in the world (except intended I/O).
- **Why Here:** Each tool is a standalone function. `web.fetch(url)` doesn't modify global state, doesn't need a class instance. This makes it easy to test, easy to understand.
- **Real Analogy:** Like a calculator — you give it numbers, it gives you a result, it doesn't remember anything.

## Files to Create/Modify

```
src/aio/
├── utils/
│   └── inject.py          ← NEW (@ expansion logic)
├── tools/
│   ├── web.py             ← NEW (web.fetch + web.search)
│   ├── patch.py           ← NEW (diff-based file editing)
│   └── registry.py        ← MODIFY (register 3 new tools)
├── tui/
│   └── app.py             ← MODIFY (@ expansion before sending)
└── cli.py                 ← MODIFY (@ expansion in `aio ask`)
```

---

## Detailed Implementation

### [NEW] `src/aio/utils/inject.py`

**Purpose:** Find `@path` tokens in a prompt and replace them with file contents.

```python
import re
from pathlib import Path

def expand_file_refs(prompt: str, cwd: Path) -> str:
    """
    Scans the prompt for @path tokens.
    
    Rules:
    - @file.py → reads the file, replaces token with contents
    - @directory/ → reads all text files in dir (git-aware)
    - @nonexistent → replaces with "[File not found: nonexistent]"
    - Lone @ or @@ → left as-is
    
    The regex pattern: @([\w./-]+) 
    This matches @ followed by word chars, dots, slashes, dashes.
    """
```

> **Junior tip:** We use `re` (regular expressions) to find `@path` tokens. The pattern `@([\w./-]+)` means: match `@` followed by one or more word characters, dots, slashes, or dashes. The parentheses create a "capture group" so we can extract just the path part.

### [NEW] `src/aio/tools/web.py`

**Purpose:** Give the AI the ability to fetch web pages and search the internet.

```python
def fetch_url(url: str, max_chars: int = 20000) -> str:
    """
    Fetches a URL and returns plain text content.
    
    Steps:
    1. Use urllib.request.urlopen (stdlib, no deps)
    2. Read the response body
    3. Strip HTML tags using a simple regex
    4. Truncate to max_chars
    
    Why urllib instead of requests:
    - Zero external dependencies (requests would add ~2MB)
    - For simple GET requests, urllib is sufficient
    - aio is a scaffold — minimizing deps is a project goal
    """

def search_web(query: str, max_results: int = 5) -> str:
    """
    Searches via DuckDuckGo's HTML lite endpoint.
    
    Why DuckDuckGo:
    - No API key required (unlike Google, Bing)
    - HTML lite page is easy to parse
    - Respects privacy
    """
```

### [NEW] `src/aio/tools/patch.py`

**Purpose:** Let the AI edit files by specifying old text → new text.

```python
def apply_patch(file_path: str, old_text: str, new_text: str) -> str:
    """
    Replaces the first occurrence of old_text with new_text in a file.
    
    Why "find and replace" instead of line numbers:
    - Line numbers change as files are edited (brittle)
    - Text matching is what the AI naturally thinks in
    - This is the same approach Claude Code's 'replace' tool uses
    
    Returns: confirmation message with the file path
    Raises: ValueError if old_text is not found in the file
    """
```

> **Junior tip:** This is called "search-and-replace" editing. The AI says "find this exact text, replace it with this new text." It's simpler and more reliable than saying "edit line 42," because line numbers shift as you add or remove lines.

### [MODIFY] `src/aio/tools/registry.py`

Add to `__init__`:
```python
self._tools["web.fetch"] = web.fetch_url
self._tools["web.search"] = web.search_web
self._tools["patch.apply"] = patch.apply_patch
```

Add schemas:
```python
self._schemas["web.fetch"] = [ToolArgSpec("url", str), ToolArgSpec("max_chars", int, required=False)]
self._schemas["web.search"] = [ToolArgSpec("query", str), ToolArgSpec("max_results", int, required=False)]
self._schemas["patch.apply"] = [ToolArgSpec("file_path", str), ToolArgSpec("old_text", str), ToolArgSpec("new_text", str)]
```

---

## Tests

### [NEW] `tests/test_inject.py`
- `test_expand_no_refs` — `"hello world"` → returned unchanged
- `test_expand_single_file` — `"explain @a.txt"` with `a.txt` containing `"hello"` → `"explain \n--- a.txt ---\nhello\n---"` (or similar format)
- `test_expand_missing_file` — `"see @ghost.txt"` → contains `"[File not found: ghost.txt]"`
- `test_expand_directory` — `"review @src/"` → all `.py` files contents injected

### [NEW] `tests/test_web_tools.py`
- `test_fetch_url_mocked` — mock `urlopen`, verify HTML tags stripped
- `test_fetch_url_max_chars` — verify output truncated at limit
- `test_search_web_mocked` — mock HTTP response, verify results parsed

### [NEW] `tests/test_patch.py`
- `test_apply_patch_replaces_text` — write file → apply → verify changed
- `test_apply_patch_not_found_raises` — old_text not in file → `ValueError`
- `test_apply_patch_only_first_occurrence` — multiple matches → only first replaced

## How to Verify Manually

1. `aio tui` → type `explain @README.md` → should see README content in the prompt
2. `\tool web.fetch url=https://example.com` → should return page content
3. Create `test.txt` with `"hello world"`, run `\tool patch.apply file_path=test.txt old_text=hello new_text=goodbye` → file should now say `"goodbye world"`
