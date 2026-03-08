# Plans

## Structure

```
plans/
├── urgent/   ← Execute at moment's notice
├── next/     ← Queued reference plans
├── done/     ← Implemented and shipped
└── README.md ← This file
```

---

## 🔴 Urgent (4 plans — ready to execute)

| Plan | What It Does |
|:--|:--|
| `phase-2-file-injection-tools.md` | `@file` injection + web.fetch/search + patch.apply tools |
| `phase-3-agent-loop-v2.md` | Real ReAct agent loop with function calling |
| `phase-4-sessions-commands.md` | Session save/resume/fork + custom commands |
| `phase-5-mcp-client-headless.md` | MCP client + headless JSON output + per-tool permissions |

## 📋 Next (4 reference plans)

| Plan | What It Covers |
|:--|:--|
| `agent-loop-sandbox-plan.md` | Path sandboxing + safety enforcement |
| `llm-provider-expansion-plan.md` | OpenAI/Anthropic provider adapters |
| `project-improvement-plan.md` | High-level 10-point improvement roadmap |
| `best-of-breed-adoption-plan.md` | Master plan: all 5 phases overview |

## ✅ Done (9 plans)

| Plan | What It Did |
|:--|:--|
| `phase-1-context-memory.md` | Added project context via .aio/context.md and `\memory` commands |
| `textual-rewrite-plan.md` | Migrated TUI from raw curses → Textual |
| `api-autoconfig-json-plan.md` | `\connect` command + `.aio/connections.json` presets |
| `header-styling-plan.md` | Custom CSS for markdown headers in TUI |
| `tab-autocomplete-plan.md` | Tab auto-completion via `SuggestFromList` |
| `history-autocomplete-plan.md` | Merged command history into suggestions |
| `contextual-editor-polish-v2-plan.md` | Dynamic keybindings for markdown panel |
| `glow-markdown-renderer.md` | Glow-style markdown + URL fetch + stash |
| `tool-contracts-plan.md` | Tool argument schemas + validation |
