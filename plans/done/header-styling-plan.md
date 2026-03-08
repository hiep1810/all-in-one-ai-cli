# Header Styling Fix for Textual Markdown

## 1. Goal Description

In the recent migration to Textual, the native `Markdown` widget renders both `# Header 1` and `## Header 2` with roughly the same text height/visual weight. The goal is to apply custom CSS overrides to make `Header 1` explicitly stand out (e.g., larger font, heavier borders, or a prominent background box) compared to lower-level headers, restoring a premium "Glow" feel.

## 2. Approach

Textual provides robust CSS targeting for its internal Markdown components. The Markdown widget dynamically creates sub-widgets like `MarkdownH1`, `MarkdownH2`, `MarkdownH3`, etc.

We can apply global CSS properties (such as padding, background colors, text alignment, or borders) to these specific components within the `AIOConsole` app's `CSS` block.

## 3. Implementation Steps

### A. Update `AIOConsole.CSS` in `src/aio/tui/app.py`
We will append explicit rules for Markdown headers:

```css
    MarkdownH1 {
        background: $accent;
        color: $text;
        border: solid $accent;
        padding: 1 2;
        content-align: center middle;
        text-style: bold;
    }
    
    MarkdownH2 {
        border-bottom: solid $accent;
        color: $text-muted;
        padding-top: 1;
        text-style: bold;
    }
```

*   **H1 (`MarkdownH1`)**: Gets a solid background, a full border, and is centered with extra padding to make it look like a massive title block.
*   **H2 (`MarkdownH2`)**: Gets a simple underline border and is left-aligned to act as a standard section divider.

### B. Verify
Launch `aio tui`, run `\md stash`, and verify that the # main title looks drastically different and larger than the ## subsections.

## 4. User Review
Please review this CSS approach. Once approved, I will inject the CSS changes into `app.py`.
