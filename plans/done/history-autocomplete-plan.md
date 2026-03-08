# Implementation Plan: Combined History and Default Auto-suggest

## 1. Goal Description

Update the interactive floating Command Suggestion dropdown to automatically combine your dynamically growing `command_history` with the existing list of default commands (`\help`, `\tool fs...`, etc.). The suggestions should prioritize your most recent, deduplicated history at the top of the list, followed by matching default commands.

## 2. Approach

We need to calculate the suggestion list dynamically every time you type, rather than relying solely on a statically loaded `self.all_commands` array.

1.  **Deduplicate History**: When the user types `/`, we take `self.command_history`, reverse it (so newest is first), and remove exact duplicates so you don't see the same command multiple times.
2.  **Filter History**: We filter this deduplicated history based on what the user is currently typing.
3.  **Filter Defaults**: We filter the static `self.all_commands` list.
4.  **Combine and Display**: We concatenate the matching History slice + the matching Defaults slice (removing any defaults that were already perfectly matched in history to avoid showing it twice).

## 3. Implementation Steps

### Update `src/aio/tui/app.py`

1.  **Refactor `on_input_changed`**:
    *   Currently, it searches `self.all_commands`.
    *   Change logic to first process `self.command_history`:
        ```python
        # Reverse and Deduplicate history
        seen = set()
        recent_unique_history = []
        for cmd in reversed(self.command_history):
            if cmd not in seen:
                seen.add(cmd)
                recent_unique_history.append(cmd)
        ```
    *   Filter `recent_unique_history` using the current `event.value`.
    *   Filter `self.all_commands` using the current `event.value`.
    *   Combine them: `matches = history_matches + [cmd for cmd in default_matches if cmd not in seen]`
    *   Populate the `OptionList` with this combined `matches` list.

## 4. Verification Plan

*   **Manual Verification**:
    1.  Type `\help` and execute. Type `\md clear` and execute.
    2.  Clear the input. Type `\`.
    3.  The dropdown should appear. The top two items should be `\md clear` and `\help` (your most recent history), followed immediately by the alphabetical list of all other default commands (like `\agent`, `\chat`, etc.).
    4.  Type `\m`. The list should show `\md clear` (history) followed by `\md open`, `\md stash` (defaults). The arrow keys should continue to work across the unified list.

## 5. User Review Required

Does prioritizing your *most recent unique history* at the top of the dropdown, followed seamlessly by the remaining *default commands*, sound like the optimal flow?
