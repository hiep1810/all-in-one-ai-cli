# Implementation Plan: Tab Auto-completion

## 1. Goal Description

Add an interactive "Tab to complete" feature to the main CLI input bar so users don't have to memorize commands or tool names. When a user types a partial command like `\t` and hits `Tab`, it should suggest or auto-fill `\tool ` or `\tools`.

## 2. Approach

Textual 0.50.0+ ships with a native system for doing exactly this in the `Input` widget using the `textual.suggester` module. We will implement `SuggestFromList`, which takes a list of strings and automatically handles the ghost-text display and `Tab` key interception natively.

## 3. Implementation Steps

### Update `src/aio/tui/app.py`

1.  **Imports**: Add `from textual.suggester import SuggestFromList`
2.  **Generate Suggestion List**: In `AIOConsole.on_mount`, we will dynamically generate a list of all valid prefix commands:
    *   Base commands: `\help`, `\clear`, `\history`, `\save`, `\chat`, `\agent`, `\workflow`, `\config`
    *   Markdown commands: `\md open`, `\md stash`, `\md clear`
    *   Dynamic tool commands: For every tool in `self.registry.list_tools()`, add `\tool <tool_name> ` to the list so users can tab-complete specific agent tools quickly.
3.  **Attach Suggester**: Assign `inp.suggester = SuggestFromList(suggestions, case_sensitive=False)` to the bottom input bar.

## 4. Verification Plan

*   **Manual Verification**:
    1.  Launch `aio tui`.
    2.  Type `\h` and press `Tab`. It should complete to `\history` or `\help`.
    3.  Type `\tool f` and press `Tab`. It should complete to `\tool fs.` (based on available filesystem tools).

## 5. User Review Required

Does this native Textual Suggestion approach look good for the Tab Auto-completion feature?
