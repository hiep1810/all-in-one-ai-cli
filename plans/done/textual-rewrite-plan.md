# Implementation Plan: Migrating TUI from Curses to Textual

## 1. Goal Description

The current TUI in `src/aio/tui/app.py` is written using Python's standard `curses` library. While functional, it is extremely difficult to support modern terminal features like native Markdown rendering, complex tables, syntax-highlighted code blocks, and scrollable UI components because `curses` operates at a primitive text-cell level. 

The goal is to scrap the `curses` implementation entirely and rewrite the TUI using [Textual](https://textual.textualize.io/), a modern Rapid Application Development framework for Python in the terminal.

## 2. Technical Benefits & Changes

*   **Native Markdown:** Textual provides a `Markdown` widget built on top of `Rich`, which automatically handles styling for tables, headers, blockquotes, and code blocks (with syntax highlighting) perfectly.
*   **Asynchronous:** Textual is async-first. This requires wrapping the current blocking LLM calls (`client.complete`) into threads (`@work` decorators) to prevent the UI from freezing during generation.
*   **Widgets & Layout:** Instead of manually calculating X/Y coordinates as done currently, we will use CSS (or Textual's layout system) to position elements (Input bar at bottom, Chat Log on left, Markdown Panel on right).
*   **Dependencies:** We will need to add `textual` (and likely upgrade `rich` if old) to `pyproject.toml`.
*   **Removal of OS-specific quirks:** `curses` handles `windows-curses` heavily differently than Unix. Textual abstract this away perfectly.

## 3. Proposed Architecture (`src/aio/tui/app.py`)

The new `aio.tui.app` will define a single `App` subclass: `AIOConsole(App)`.

### Core Widgets:
1.  **`Header`**: Top bar showing current project/status.
2.  **`RichLog` (Chat Area)**: The main central area where chat messages (`> hello`, `ai> ...`) and tool outputs are written. 
3.  **`Input`**: The bottom input bar where users type commands. It supports native cursor movement, deletion, and history out of the box.
4.  **`Markdown` (Side Panel)**: A conditionally visible panel on the right side. When `\md open` or `\md stash` is run, this is toggled visible and populated.
5.  **`Footer`**: Bottom bar showing contextual keybindings.

### State Management
*   We'll maintain the `TUIContext` object to hold the `AgentExecutor`, `ToolRegistry`, `AuditLogger`, etc.
*   The `Input` widget will trigger an `on_input_submitted` event.
*   **Async execution:** Long-running tasks (LLM completion, agent runs) will use `self.run_worker(thread=True)` to execute standard synchronous python code in the background, updating the `RichLog` progressively (or via textual message queues for streaming).

### Mapping Existing Features

*   `\help`, `\clear`, `\tools`, `\history` -> Simple methods writing directly to `RichLog`.
*   `\md open <path>` -> Read path, send string to `Markdown` widget, set `display=True`.
*   `\agent run` -> Launch a worker thread, disable `Input`, write yield steps to `RichLog`, re-enable `Input`.
*   **Approvals:** The input loop can set a state flag (`awaiting_approval=True`). The next enter press routes to the approval logic instead of general execution.
*   **Tabs / Autocomplete:** Textual's `Input` can be extended to handle `Tab` presses via the `on_key` event to provide suggestions.

## 4. Work Phases

### Phase 1: Foundation & Dependencies
*   Update `pyproject.toml` to depend on `textual>=0.50.0`. 
*   Update `cli.py` to remove the `windows-curses` try/except block.
*   Create a basic shell `app.py` with the Header, Footer, Input, and RichLog to verify the app launches.

### Phase 2: Core Loop Migration
*   Migrate `execute_line` logic into the new App.
*   Wire up standard text chat to use the LLM Router and write basic `RichLog.write(Markdown(...))` responses.
*   Implement command parsing (`\tools`, `\clear`, etc.).

### Phase 3: The Markdown Super-Panel
*   Implement the right-side split layout.
*   Wire `\md open`, `\md stash`, and URL requests to populate the `Markdown` widget.
*   Textual automatically handles the `j`/`k`, `PageUp/Down` scrolling logic when the widget is focused! No need for manual state tracking.

### Phase 4: Polish
*   Implement the tool approval flow.
*   Implement the Tab-autocomplete logic if strictly needed, or suggest a simpler command-palette alternative using `Modal` dialogs.

## 5. User Review Required

> [!WARNING]
> This is a full rewrite of the UI layer. The visual feel will change significantly, feeling much closer to modern apps (like `k9s` or `lazydocker`) rather than raw BBS terminals.
> Textual uses CSS for styling, so custom themes ( neon, matrix ) will need to be redefined using Textual theme variables instead of curses color pairs.
> Are you ready to proceed with the Textual refactor?
