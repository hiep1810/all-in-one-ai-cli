# Project Improvement Plan

## 1. Stable TUI Spec
- Freeze one canonical keymap and interaction model.
- Add in-app `\keys` to show live bindings.
- Auto-test keybindings so future UI refactors do not break controls.

## 2. Agent Loop Upgrade
- Replace demo executor with iterative loop (`plan -> act -> observe -> replan`).
- Add max-step budgets and failure categories.
- Add resumable runs from saved state.

## 3. Tool Ecosystem
- Add web/search tool with citations.
- Add git-native tools (`status`, `diff`, `commit draft`, `branch summary`).
- Add SQL/CSV tool adapters for data tasks.

## 4. Memory That Matters
- Session summaries every N messages.
- Project memory store: architecture notes, decisions, TODO map.
- Retrieval command: `\memory ask <question>` for contextual grounding.

## 5. Better Markdown Workspace
- Split modes: preview, raw editor, diff view.
- Watch file changes and auto-refresh preview.
- Export panel to HTML/PDF from inside TUI.

## 6. MCP Expansion
- Add write-safe tools with approval gates.
- Add scoped permissions profiles per MCP client.
- Add MCP health endpoint and self-check command.

## 7. Safety and Governance
- Policy profiles (`safe`, `dev`, `autonomous`).
- Path and command allowlists enforced centrally.
- Redact secrets in logs/replay by default.

## 8. DX and Reliability
- Add `aio doctor` to verify environment, model endpoint, MCP wiring.
- Add integration tests for TUI flows and streaming.
- Add benchmark command for latency/token throughput.

## 9. Multi-Provider Routing
- Add OpenAI/Anthropic providers behind same interface.
- Task-based model routing (chat/coding/research).
- Automatic fallback on timeout/5xx.

## 10. Productization
- Add plugin SDK for custom tools/workflows.
- Versioned workflow schema and migration tooling.
- Add telemetry toggle and lightweight usage analytics.

## Suggested Next Step
- Convert this plan into a prioritized 2-week execution board (P0/P1/P2) with exact tickets and commit order.
