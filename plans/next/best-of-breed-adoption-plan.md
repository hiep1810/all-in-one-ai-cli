# Best-of-Breed Feature Adoption Plan

## 🛠️ Execution Status: Executing
### 🔍 Points of Uncertainty
* None identified — all source files, tests, roadmap, and competitor docs have been reviewed.

---

## Goal

Adopt the most impactful features from Claude Code, Gemini CLI, and OpenCode into the aio CLI project. Organized into 5 **Phases**, each self-contained and testable. Phases are ordered so earlier phases create foundations needed by later ones.

---

## Phase 1 — Context & Memory (Foundation)

> **Inspired by:** Claude Code (`CLAUDE.md`), Gemini CLI (`GEMINI.md`)
>
> **Why first:** Everything else (agent loop, MCP client, session mgmt) benefits from persistent project context. This is zero-dependency and low-risk.

### Component: Project Context System

---

#### [NEW] [context.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/memory/context.py)

A loader that discovers and loads `.aio/context.md` files hierarchically (global `~/.aio/context.md` → project `.aio/context.md` → subdirectory `.aio/context.md`). Concatenates them into a single system prompt. Also supports `\memory add <text>` to append facts.

**Pattern:** Hierarchical config merge (same as CLAUDE.md/GEMINI.md)

- `load_project_context(project_root: Path) → str` — walks up from cwd to find `.aio/context.md` files
- `append_memory(fact: str, path: Path) → Path` — appends a line to the project's context file

#### [MODIFY] [schema.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/config/schema.py)

No changes needed — context is loaded separately from config.

#### [MODIFY] [app.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/tui/app.py)

Add `\memory` commands: `\memory show`, `\memory add <text>`, `\memory refresh`

#### [MODIFY] [client.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/llm/client.py)

Inject context as a `system` message in the `_payload()` messages array.

---

## Phase 2 — @ File Injection + New Tools

> **Inspired by:** Gemini CLI (`@path`), OpenCode (`fetch`, `diagnostics`), Claude Code (`web_fetch`)
>
> **Why second:** Tools are the building blocks the agent loop needs. @ injection is a huge DX win.

### Component A: @ File Injection

---

#### [MODIFY] [app.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/tui/app.py)

Before sending a chat prompt, scan for `@path/to/file` tokens. Replace each with the file's contents (like Gemini CLI's `read_many_files`). Use git-aware filtering to skip `.gitignore`d files when `@directory/` is used.

#### [MODIFY] [cli.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/cli.py)

Same @ expansion in `aio ask "explain @src/main.py"`.

#### [NEW] [inject.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/utils/inject.py)

`expand_file_refs(prompt: str, cwd: Path) → str` — finds `@path` tokens, reads files, injects content. Shared by CLI and TUI.

### Component B: New Built-in Tools

---

#### [NEW] [web.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/tools/web.py)

Two tools:
- `web.fetch(url: str, max_chars: int = 20000) → str` — fetches a URL using `urllib`, strips HTML tags to plain text
- `web.search(query: str, max_results: int = 5) → str` — DuckDuckGo search via their HTML lite endpoint (no API key needed)

#### [NEW] [patch.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/tools/patch.py)

Diff-based file editing:
- `patch.apply(file_path: str, old_text: str, new_text: str) → str` — replaces the first occurrence of `old_text` with `new_text` in a file

#### [MODIFY] [registry.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/tools/registry.py)

Register new tools: `web.fetch`, `web.search`, `patch.apply`. Update schemas.

---

## Phase 3 — Real Agent Loop + Function Calling

> **Inspired by:** Claude Code (tool-use API), Gemini CLI (function declarations), OpenCode (tool chaining)
>
> **Why third:** After Phase 2 gives us more tools and context, the agent can actually *do* things.

### Component: Agent Loop V2

---

#### [MODIFY] [client.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/llm/client.py)

Add `chat_with_tools(messages: list[dict], tools: list[dict]) → dict` method to `LlamaCppClient`. This sends the OpenAI-compatible function calling format:
- `tools` parameter with JSON schemas for each tool
- Parses `tool_calls` from the response
- Returns structured response with `{role, content, tool_calls}`

#### [MODIFY] [executor.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/agent/executor.py)

Replace the stub with a real iterative loop:

```
1. Build system prompt (from context.md)
2. Send goal + tools to LLM via chat_with_tools()
3. LOOP (max_steps):
   a. If LLM returns tool_calls → validate, safety-check, execute each
   b. Append tool results to messages
   c. Send updated messages back to LLM
   d. If LLM returns final text (no tool_calls) → return result
4. If max_steps exceeded → return partial result with reason
```

#### [MODIFY] [planner.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/agent/planner.py)

Replace stub with actual function that converts `ToolRegistry.list_tools()` + schemas into OpenAI-compatible tool declarations. This is what gets sent to the LLM.

#### [MODIFY] [schema.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/config/schema.py)

Add `agent_max_steps: int = 10` to Config.

---

## Phase 4 — Session Management + Custom Commands

> **Inspired by:** Claude Code (`--resume`, `/chat save`), Gemini CLI (`/resume`), OpenCode (SQLite sessions, MD custom commands)
>
> **Why fourth:** Now that the agent actually works, users need to save/resume sessions and create shortcuts.

### Component A: Session Management

---

#### [MODIFY] [session_store.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/memory/session_store.py)

Extend `SessionStore` with:
- `list_sessions() → list[dict]` — returns session names + metadata (line count, last modified)
- `load(session: str) → list[dict]` — reads all messages from a session
- `delete(session: str) → bool` — deletes a session file
- `fork(source: str, target: str) → Path` — copies a session to a new name

#### [MODIFY] [app.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/tui/app.py)

Add commands:
- `\session list` — show saved sessions
- `\session save <name>` — save current conversation
- `\session resume <name>` — load and continue a session
- `\session delete <name>` — delete a session
- `\compact` — summarize current context using LLM (inspired by OpenCode's auto-compact)

#### [MODIFY] [cli.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/cli.py)

Add `--resume <session>` flag to `aio ask` and `aio chat`.

### Component B: Custom Commands

---

#### [NEW] [commands.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/config/commands.py)

Custom commands stored as markdown files:
- **User-level:** `~/.aio/commands/*.md`
- **Project-level:** `.aio/commands/*.md`
- File name = command name, file content = prompt template
- Supports `$ARG_NAME` placeholders (like OpenCode)

Functions:
- `discover_commands(project_root: Path) → dict[str, CommandDef]`
- `expand_command(cmd: CommandDef, args: dict[str, str]) → str`

#### [MODIFY] [app.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/tui/app.py)

Add `\command <name> [args]` — loads and executes a custom command.

#### [MODIFY] [command_palette.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/tui/command_palette.py)

Include discovered custom commands in the palette options.

---

## Phase 5 — MCP Client + Headless Output

> **Inspired by:** Claude Code (`--mcp-config`), Gemini CLI (`@server`), OpenCode (stdio + SSE MCP)
>
> **Why last:** This is the highest-effort feature and depends on a working agent loop (Phase 3).

### Component A: MCP Client

---

#### [NEW] [mcp/client.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/mcp/client.py)

A client that connects to external MCP servers. Supports stdio transport:
- `MCPClient(command: str, args: list[str], env: dict)`
- `connect()` — spawns the process, sends `initialize`
- `list_tools() → list[dict]` — calls `tools/list`
- `call_tool(name: str, arguments: dict) → dict` — calls `tools/call`
- `close()` — terminates the process

#### [NEW] [mcp/manager.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/mcp/manager.py)

Reads `.aio/mcp.json` config (same format as existing `mcp.example.json`), starts all configured MCP servers, and manages their lifecycle.

- `MCPManager(config_path: Path)`
- `start_all()` — spawns all configured servers
- `get_all_tools() → dict[str, list[dict]]` — tool discovery per server
- `call(server: str, tool: str, args: dict) → dict`
- `stop_all()`

#### [MODIFY] [registry.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/tools/registry.py)

After loading built-in tools, also load MCP tools from `MCPManager`. Prefix MCP tools with server name: `github.list_prs`, `slack.send_message`.

#### [MODIFY] [app.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/tui/app.py)

Add `\mcp list`, `\mcp refresh` commands.

### Component B: Headless JSON Output

---

#### [MODIFY] [cli.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/cli.py)

Add `--output-format` flag to `aio ask`:
- `text` (default) — current behavior
- `json` — `{"result": "...", "model": "...", "tokens": ...}`
- `stream-json` — newline-delimited JSON events

### Component C: Per-Tool Permissions

---

#### [MODIFY] [safety.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/agent/safety.py)

Replace hardcoded `RISKY_TOOLS` set with a configurable permission map:
- Read from `.aio/config.yaml` under `tool_permissions`
- Support `allow`, `deny`, `ask` per tool name or glob pattern
- Example: `tool_permissions: {shell.*: ask, fs.read: allow, web.*: deny}`

#### [MODIFY] [schema.py](file:///d:/H%20Drive/git/all-in-one-ai-cli/src/aio/config/schema.py)

Add `tool_permissions: dict[str, str]` to Config with sensible defaults.

---

## Summary: Files Changed Per Phase

| Phase | New Files | Modified Files | Estimated LOC |
|:--|:--|:--|:--|
| 1. Context & Memory | `memory/context.py` | `app.py`, `client.py` | ~120 |
| 2. @ Injection + Tools | `utils/inject.py`, `tools/web.py`, `tools/patch.py` | `app.py`, `cli.py`, `registry.py` | ~250 |
| 3. Agent Loop V2 | — | `client.py`, `executor.py`, `planner.py`, `schema.py` | ~300 |
| 4. Sessions + Commands | `config/commands.py` | `session_store.py`, `app.py`, `cli.py`, `command_palette.py` | ~250 |
| 5. MCP Client + Headless | `mcp/client.py`, `mcp/manager.py` | `registry.py`, `app.py`, `cli.py`, `safety.py`, `schema.py` | ~400 |
| **Total** | **7 new files** | **~12 modified files** | **~1,320 LOC** |

---

## Verification Plan

### Automated Tests

All tests use `pytest`. Run with:
```bash
cd "d:\H Drive\git\all-in-one-ai-cli"
.venv\Scripts\activate
pytest tests/ -v
```

#### Phase 1 Tests

| Test File | What It Tests | Command |
|:--|:--|:--|
| [NEW] `tests/test_context.py` | `load_project_context` discovers and concatenates `.aio/context.md` files; `append_memory` appends facts | `pytest tests/test_context.py -v` |

Specific test cases:
- `test_load_context_missing_file_returns_empty` — no context.md → empty string
- `test_load_context_reads_project_file` — create `.aio/context.md` in tmp_path, verify it's read
- `test_append_memory_creates_and_appends` — append two facts, verify both are in file

#### Phase 2 Tests

| Test File | What It Tests | Command |
|:--|:--|:--|
| [NEW] `tests/test_inject.py` | `expand_file_refs` replaces `@path` with file contents | `pytest tests/test_inject.py -v` |
| [NEW] `tests/test_web_tools.py` | `web.fetch` returns content; `web.search` returns results (mocked HTTP) | `pytest tests/test_web_tools.py -v` |
| [NEW] `tests/test_patch.py` | `patch.apply` replaces old_text with new_text in file | `pytest tests/test_patch.py -v` |
| [MODIFY] `tests/test_tools.py` | Registry now includes `web.fetch`, `web.search`, `patch.apply` | `pytest tests/test_tools.py -v` |

Specific test cases:
- `test_expand_no_refs` — prompt without `@` → returned unchanged
- `test_expand_single_file_ref` — `"explain @README.md"` → file contents injected
- `test_expand_missing_file_ref` — `@nonexistent.txt` → error message inline
- `test_patch_apply_replaces_text` — write file, apply patch, verify content changed
- `test_web_fetch_mocked` — mock `urllib.request.urlopen`, verify HTML stripping

#### Phase 3 Tests

| Test File | What It Tests | Command |
|:--|:--|:--|
| [MODIFY] `tests/test_agent.py` | Agent loop runs multiple steps, handles tool calls, respects `max_steps` | `pytest tests/test_agent.py -v` |

Specific test cases:
- `test_agent_loop_max_steps` — mock LLM to always return tool_calls → verify loop stops at max_steps
- `test_agent_loop_final_response` — mock LLM to return text on 2nd call → verify result returned
- `test_agent_loop_safety_block` — tool_call for `shell.exec` in strict mode → verify blocked

#### Phase 4 Tests

| Test File | What It Tests | Command |
|:--|:--|:--|
| [NEW] `tests/test_session.py` | Session list/load/delete/fork | `pytest tests/test_session.py -v` |
| [NEW] `tests/test_commands.py` | Custom command discovery and expansion | `pytest tests/test_commands.py -v` |

Specific test cases:
- `test_session_list_returns_metadata` — create 2 session files, verify list returns both with metadata
- `test_session_load_returns_messages` — append 3 messages, load, verify all 3 returned
- `test_session_fork_copies_data` — append messages, fork, verify copy has same content
- `test_discover_commands_from_project` — create `.aio/commands/fix.md`, verify discovered as `project:fix`
- `test_expand_command_replaces_args` — template with `$FILE`, expand with `main.py`, verify substitution

#### Phase 5 Tests

| Test File | What It Tests | Command |
|:--|:--|:--|
| [NEW] `tests/test_mcp_client.py` | MCP client connect, tool discovery, tool call (mocked subprocess) | `pytest tests/test_mcp_client.py -v` |
| [MODIFY] `tests/test_cli.py` | `--output-format json` produces valid JSON | `pytest tests/test_cli.py -v` |
| [MODIFY] `tests/test_safety.py` | Per-tool permissions from config | `pytest tests/test_safety.py -v` |

Specific test cases:
- `test_mcp_client_list_tools` — mock stdio, send tools/list response, verify parsed
- `test_mcp_client_call_tool` — mock stdio, send tools/call response, verify result
- `test_ask_json_output` — `aio ask "hello" --output-format json` → valid JSON with `result` key
- `test_tool_permissions_allow_glob` — `shell.*: ask` config → `shell.exec` requires approval

### Full Suite Regression

After all 5 phases:
```bash
pytest tests/ -v --tb=short
```

All existing 8 test files must still pass (backward compatibility).

### Manual Verification

> [!IMPORTANT]
> These are optional smoke tests the user can run after each phase.

**Phase 1:** Create `.aio/context.md` with "Always respond in Vietnamese", run `aio tui`, type `hello` → verify AI includes the context.

**Phase 2:** Run `aio tui`, type `explain @README.md` → verify file contents are injected into the prompt. Type `\tool web.fetch url=https://example.com` → verify content returned.

**Phase 3:** Run `aio agent run "list all Python files in this project" --approve-risky` → verify agent calls `shell.exec` or `fs.search` and returns actual file list.

**Phase 4:** In TUI: `\session save test1`, exit, reopen, `\session resume test1` → verify conversation restored. Create `.aio/commands/greet.md` with `Say hello to $NAME`, type `\command greet NAME=Hiep`.

**Phase 5:** Add an MCP server to `.aio/mcp.json`, run `aio tui`, type `\mcp list` → verify server tools appear. Run `aio ask "hello" --output-format json` → verify JSON output.
