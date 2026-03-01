# Glow-Style Native Markdown Renderer for `aio tui`

This document outlines the plan to upgrade the markdown rendering capabilities within the `all-in-one-ai-cli` TUI to match the aesthetics and behavior of [Glow](https://github.com/charmbracelet/glow) natively via Python's `textual` and `rich`, without relying on an external binary.

## 1. Goal Description

Currently, the TUI uses a basic `Markdown` widget in a side-panel, which simply renders available text given an absolute path via the `\\md open` command.

The goal is to deeply customize the Textual Markdown rendering to achieve a premium, Glow-like visual style, and to expand the scope to support fetching markdown from the internet, discovering local markdown files via a "stash" selector, and implementing a robust, cross-platform keybinding strategy.

## 2. Implementation Approach: Native Python (Textual & Rich)

Instead of wrapping the Go `glow` binary, we will natively recreate the experience:
1.  **Custom CSS/Theming:** We will override the default Textual Markdown CSS styles to match Charm's aesthetic (margins, padding, colors, blockquotes, code block syntax highlighting themes like Dranula or Neon).
2.  **Custom Textual Markdown Blocks:** If necessary, we can sub-class Textual's markdown renderer or use underlying `rich.markdown` capabilities to get the layout perfectly matched to a reading view.

## 3. Feature Scope Expansion

### A. Fetching Markdown from URLs
*   We will add support for HTTP/HTTPS requests directly within the TUI command `\\md open <url>`.
*   **Mechanism:** When `<url>` is detected, we use `httpx` or `urllib.request` to lazily fetch the raw document content from the web asynchronously, handle potential errors (404, timeouts), and feed the string into the markdown widget.
*   **Use-case:** Loading an online `README.md` or fetching a gist.

### B. "Stash" Mode (Discovering Files)
*   *Explanation:* "Stash" is a Glow concept where the app automatically finds local markdown files in the current working directory or a centralized location and allows the user to browse them in a list before opening one.
*   **Implementation:** 
    *   Create a command like `\\md stash`.
    *   This will display a new Textual `ListView` or `DataTable` inside the markdown panel (or a modal), paginated showing `.md` files found via `aio.tools.filesystem.list_files` (or `pathlib.Path.rglob`).
    *   Users scroll through the stash, hit `Enter` to open a file.

## 4. Keybinding Strategy (Linux, WSL, macOS)

A good keybinding strategy needs to work universally across terminal emulators (iTerm2, Windows Terminal, GNOME Terminal) which notoriously handle modifier keys differently. The safest, most cross-platform approach is to adopt Vim-like navigation which relies on un-modified alphabet keys, reducing conflict with terminal shortcuts or OS specific bindings.

**Proposed Strategy for Markdown Panel (When Focused):**

*   `j` / `k` : Scroll Down / Scroll Up (1 line)
*   `Space` / `PageDown` : Page down
*   `u` / `d` / `PageUp` : Half-page up/down
*   `g` : Go to top (`gg` in Vim, we could bind `g` to top for simplicity)
*   `G` : Go to bottom
*   `/` : Open search bar at the bottom of the panel
*   `n` / `N` : Next / Previous search match
*   `Esc` (or `q`): Exit focus or close stash view
*   `Tab` / `Shift+Tab`: Switch focus rapidly between input bar and markdown view.

**Why this works cross-platform:**
*   Alphabet keystrokes are registered cleanly via `stdin` universally.
*   `Ctrl+...` bindings are highly prone to conflicts (e.g., `Ctrl+W` closes tabs in many setups, `Ctrl+C` kills processes, `Ctrl+O` sometimes blocked).
*   By relying on typical pager/Vim keys while the markdown viewer is *focused*, we completely bypass OS-level quirks affecting complex chords.

## 5. Architectural Changes & Refactoring

*   **`src/aio/tui/app.py`**:
    *   Add a new state parameter or a sub-widget stack for the markdown panel to switch between `Markdown Viewer`, `URL Loading Spinner`, and `Stash List`.
    *   Add HTTP fetching logic (perhaps injecting a new `aio.utils.network` helper or using an existing tool).
    *   Apply the new global key bindings when the Markdown widget is focused.
    *   Create a specific `CustomMarkdown` class inherited from Textual's `Markdown` to apply Glow-like styling options programmatically, decoupling from the main `App` logic if complex.

## 6. Verification Plan

*   **Manual Testing:**
    *   Run `aio tui` and open a local `README.md`. Verify margins, code blocks, and blockquotes look stylish (Glow-esque).
    *   Run `\\md open https://raw.githubusercontent.com/.../README.md`. Verify it fetches, handles errors gracefully, and displays.
    *   Run `\\md stash`. Verify a paginated file list appears, is navigable with keys, and successfully opens a selected file.
    *   *Cross-platform validation:* Check that `j/k`, `Tab` focus switching works without triggering unwanted terminal events in testing environments (bash on Linux, zsh on Mac, WSL terminal).
*   **Unit Tests:**
    *   Test url-validation and url-fetching edge cases.
    *   Test the backend directory traversal for the "Stash".
