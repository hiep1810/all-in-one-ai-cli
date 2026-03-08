# Implementation Plan: Contextual Editor Polish v2

## 1. Goal Description

1. **Contextual Shortcuts**: "Toggle Focus (Chat/MD)" (`ctrl+o`) and "Edit MD" (`e`) should only be visible and active if there is _actually a markdown file currently loaded and displayed_. When you are just chatting without loading a file via `\md open`, these bindings should be completely hidden from the footer.
2. **Missing Focus Border**: When navigating to the Markdown view (using `Ctrl+O`), there's no visual indication that it actually has keyboard focus. We previously added CSS, but Textual wraps the `Markdown` widget internally, which can sometimes swallow DOM focus pseudo-states.

## 2. Approach

1.  **Dynamic Binding for Reader Mode**:
    *   Initialize the app *without* the `ctrl+o` or `e` bindings showing in the footer.
    *   In `_handle_markdown_command`, when the user runs `\md open` or `\md stash` and successfully loads content into the right panel, we dynamically `self.bind("ctrl+o", ...)` and `self.bind("e", ...)` to reveal the shortcuts organically. 
    *   When the user types `\md clear` to close the panel, we gracefully `del` the bindings using the same unbinding logic we created for the editor mode.
2.  **CSS Border Fix Focus pseudo-class**: 
    *   When `app.action_toggle_markdown_focus()` moves focus to the `Markdown` or `TextArea` widgets, Textual natively adds a `.focus` CSS class to the focused widget (in addition to the standard `:focus` pseudoclass). We will update the CSS selector to target `.focus` on the wrapper containers instead of just `:focus` on the content elements.

## 3. Implementation Steps

### Update `src/aio/tui/app.py`

1.  **Update CSS Focus Rules**:
    Fix the border selectors to use Textual's `.focus` state instead of, or in addition to, the browser-level pseudo-selector:
    ```css
    #md-view {
        /* ... existing styles ... */
        border: solid panel;
    }
    #md-view:focus-within {
        border: solid $accent;
    }
    ```
    Actually, managing it on the container `#md-view` is much more foolproof than trying to capture focus bouncing between its two internal child DOM nodes.
    
2.  **Adjust Bindings**:
    *   Remove `ctrl+o` and `e` from static `BINDINGS` array. Let's start with a completely pristine canvas showing only `Clear Log` and `Command Palette`!
    *   Create a helper method `def _manage_md_bindings(self, visible: bool) -> None:` that adds them (`show=True`) when `visible` is true, and scrubs them away using the dictionary key deletion technique otherwise.
    *   Call `self._manage_md_bindings(True)` during `\md open` and `\md stash` branches.
    *   Call `self._manage_md_bindings(False)` during `\md clear` branch.

## 4. Verification Plan

*   **Manual Verification**:
    1.  Start the app. The footer should be extremely clean: just `Clear Log` and `Command Palette`.
    2.  Type `\md open README.md`. As the text loads, the `Toggle Focus` and `Edit MD` tags should gracefully pop in.
    3.  Press `Ctrl+O`. The entire Markdown panel container should cleanly highlight with a bright blue `$accent`.
    4.  Type `\md clear`. The border, view, and footer tags should all disappear simultaneously, returning you back to a pure chat state.

## 5. User Review Required

Do these fixes for contextual toggling and clean container borders align exactly with your goals?
