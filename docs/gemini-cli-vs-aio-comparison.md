# AI Terminal Tools — Brutally Honest 4-Way Comparison

## 🛠️ Execution Status: Executing
### 🔍 Points of Uncertainty
* None identified — all four project docs were read directly from their source repos/docs.

---

## The Players

| | **Claude Code** | **Gemini CLI** | **OpenCode** | **aio (yours)** |
|:--|:--|:--|:--|:--|
| Backed by | Anthropic | Google | Charmbracelet (archived → Crush) | Solo dev |
| Language | TypeScript | TypeScript | Go | Python |
| License | Proprietary | Apache 2.0 | MIT | — |
| Install | curl / brew / winget | npm | go install / brew / curl | `pip install -e .` |
| Maturity | **Production** (massive user base) | **Production** (563+ contributors) | **Archived** (moved to Crush) | **Early scaffold** |
| Stars | ~40k+ | ~50k+ | ~5k | ~0 |

---

## Feature-by-Feature Comparison

> **Legend:** ✅ Implemented | 🔶 Partial/Basic | ❌ Not present | 📋 Roadmap
>
> **Best** column shows who does it best. **Honest rating** = brutally honest.

| # | Feature | Claude Code | Gemini CLI | OpenCode | **aio** | Best |
|:--|:--|:--|:--|:--|:--|:--|
| **Core** |||||||
| 1 | AI Provider Support | ❌ Claude only | ❌ Gemini only | ✅ **8 providers** (OpenAI, Claude, Gemini, Bedrock, Groq, Azure, Copilot, Vertex) | 🔶 llama.cpp + OpenAI-compat | **OpenCode** |
| 2 | Self-Hosted / Local AI | ❌ | ❌ | ✅ OpenAI-compat endpoint | ✅ llama.cpp + `\connect` presets | **Tie (OC/aio)** |
| 3 | Model Selection at Runtime | ✅ `--model` + fallback | ✅ `-m` flag + `/model` | ✅ Config per agent role | 🔶 Config file only | **Claude Code** |
| **TUI & UX** |||||||
| 4 | Interactive TUI | ✅ Ink-based | ✅ Ink-based | ✅ BubbleTea (polished) | 🔶 Raw curses (functional, fragile) | **OpenCode** |
| 5 | TUI Themes | ✅ `/theme` dialog | ✅ `/theme` | ❌ | ✅ 3 themes (neon/minimal/matrix) | **Tie (CC/GC/aio)** |
| 6 | Markdown Rendering | ✅ Built-in | ✅ Built-in | ✅ Built-in | ✅ Side-panel raw/rendered toggle | **aio** (unique dual-panel) |
| 7 | Vim Mode | ❌ | ✅ Full vim bindings | ✅ Vim-style editor | ❌ | **Gemini CLI** |
| 8 | Keyboard Shortcuts | ✅ Extensive | ✅ Extensive | ✅ Extensive (vim-like nav everywhere) | ✅ Good (Ctrl+S select, Ctrl+R search) | **Tie** |
| **Agent & Tools** |||||||
| 9 | Agentic Coding (auto edit/run/fix) | ✅ **Best-in-class** — writes tests, runs them, fixes failures autonomously | ✅ Good — file edit + shell + search | 🔶 Basic tool chaining | 🔶 `AgentExecutor` with plan-act-observe (structure exists, LLM integration is mock/basic) | **Claude Code** |
| 10 | Sub-Agents / Multi-Agent | ✅ `--agents` flag, custom roles, per-agent tools/model/MCP | ❌ | ❌ | 📋 P2 roadmap (planner/executor/reviewer) | **Claude Code** |
| 11 | Built-in Tools | ✅ Read/Edit/Write/Bash/Grep/Glob/LS/WebFetch/Search/TodoList | ✅ 15 tools (fs, shell, web, search, memory, planning, ask_user) | ✅ 13 tools (glob, grep, ls, view, write, edit, diagnostics, bash, fetch, sourcegraph, agent) | 🔶 5 categories (fs.read/search, shell.exec, git.log/diff/show, csv.query, sql.query) | **Gemini CLI** |
| 12 | Plan Mode (read-only research) | ✅ `--permission-mode plan` | ✅ `/plan` with enter/exit | ❌ | ❌ | **Claude Code** |
| 13 | Tool Validation / Schema | ✅ | ✅ | ✅ | ✅ | **Tie** |
| **Context & Memory** |||||||
| 14 | Project Context Files | ✅ `CLAUDE.md` (hierarchical, auto-memory) | ✅ `GEMINI.md` (hierarchical, `/memory` commands) | ❌ | ❌ | **Claude Code** |
| 15 | Auto Memory / Learning | ✅ Auto-memory (saves facts) | ✅ `save_memory` tool | ❌ | ❌ | **Claude Code** |
| 16 | Context Compression | ✅ `/compact` | ✅ `/compress` | ✅ Auto-compact at 95% context | ❌ | **OpenCode** (automatic) |
| 17 | Token Caching | ❌ | ✅ | ❌ | ❌ | **Gemini CLI** |
| 18 | @ File Injection | ❌ | ✅ `@path` into prompt | ❌ | ❌ | **Gemini CLI** |
| **Sessions & History** |||||||
| 19 | Session Management | ✅ Resume/continue/fork with `--resume`/`-c` | ✅ `/chat save/resume/list/delete` + `/resume` browser | ✅ SQLite-backed, multi-session | 🔶 Append-only `SessionStore` | **Claude Code** |
| 20 | Conversation Checkpointing | ✅ Auto + manual | ✅ `/chat save` + `/restore` for file rollback | ❌ | ❌ | **Claude Code** |
| 21 | Conversation Rewind | ✅ | ✅ `/rewind` (Esc×2) | ❌ | ❌ | **Tie (CC/GC)** |
| 22 | Audit / Replay Logs | ❌ | 🔶 | ❌ | ✅ `aio replay` with structured JSON logs | **aio** |
| **Integration & Extensibility** |||||||
| 23 | MCP Client (use external tools) | ✅ Full MCP client + `--mcp-config` | ✅ Full MCP client + `@server` prefix | ✅ MCP client (stdio + SSE) | ❌ | **Claude Code** |
| 24 | MCP Server (expose own tools) | ❌ | ❌ | ❌ | ✅ `aio-mcp` stdio server | **aio** (unique) |
| 25 | LSP Integration | ❌ | ❌ | ✅ Language Server diagnostics, multi-lang | ❌ | **OpenCode** (unique) |
| 26 | GitHub / CI Integration | ✅ GitHub Actions + GitLab CI + `@Claude` in PRs + Slack | ✅ GitHub Action + `@gemini-cli` in PRs | ❌ | 📋 P2 roadmap | **Claude Code** |
| 27 | IDE Integration | ✅ VS Code + JetBrains + Desktop app | ✅ VS Code companion | ❌ | ❌ | **Claude Code** |
| 28 | Plugins / Extensions | ✅ Plugin system (`--plugin-dir`) | ✅ Extensions (install/manage/update) | ❌ | ❌ | **Claude Code** |
| 29 | Custom Commands | ✅ Custom slash commands (skills) | ✅ TOML-based custom commands | ✅ MD-based with named args (user: / project: scope) | ❌ | **OpenCode** |
| 30 | Skills System | ✅ Custom skills + built-in | ✅ `/skills` enable/disable/reload | ❌ | ❌ | **Claude Code** |
| 31 | Hooks / Lifecycle Events | ✅ Hooks system | ✅ `/hooks` | ❌ | ❌ | **Tie (CC/GC)** |
| **Scripting & Automation** |||||||
| 32 | Non-Interactive / Headless Mode | ✅ `-p` flag, piping, JSON/stream-JSON output, budget caps, max turns | ✅ `-p` flag, JSON/stream-JSON output | ✅ `-p` flag, JSON/text output, quiet mode | 🔶 `aio ask` one-shot only | **Claude Code** |
| 33 | Structured Output | ✅ `--json-schema` for typed output | ✅ `--output-format json` | ✅ `--format json` | ❌ | **Claude Code** |
| 34 | Workflow / Pipeline Engine | ❌ | ❌ | ❌ | ✅ YAML workflow runner | **aio** (unique) |
| 35 | Budget / Cost Control | ✅ `--max-budget-usd` | ❌ | ❌ | ❌ | **Claude Code** (unique) |
| **Safety & Security** |||||||
| 36 | Permission / Safety System | ✅ Per-tool allow/deny, permission modes (plan/auto/default), `--allowedTools` | ✅ Sandboxing, trusted folders, `/permissions` | ✅ Permission dialog, auto-approve in headless | 🔶 3 levels (off/confirm/strict) — coarse-grained | **Claude Code** |
| 37 | Remote / Cross-Device | ✅ Remote control, `/teleport`, web/iOS/desktop/Slack/Chrome | ❌ | ❌ | ❌ | **Claude Code** (unique) |
| **Content & Search** |||||||
| 38 | Web Search | ❌ | ✅ `google_web_search` (native grounding) | ❌ | ❌ | **Gemini CLI** |
| 39 | Web Fetch | ✅ (via bash curl etc, not a dedicated tool) | ✅ `web_fetch` built-in | ✅ `fetch` tool built-in | ❌ | **Gemini CLI** |
| 40 | Code Search (Sourcegraph etc.) | ❌ | ❌ | ✅ `sourcegraph` tool built-in | ❌ | **OpenCode** (unique) |
| 41 | Multimodal (images/PDFs/audio) | ✅ Images | ✅ Images, PDFs, audio | ❌ | ❌ | **Gemini CLI** |
| 42 | Stats / Telemetry | ✅ Token tracking | ✅ `/stats session/model/tools` | ❌ | 🔶 Audit logger only | **Gemini CLI** |

---

## Summary Scorecard

| Metric | Claude Code | Gemini CLI | OpenCode | **aio** |
|:--|:--|:--|:--|:--|
| **"Best" wins** | **18** | **8** | **5** | **4** |
| **Unique features** | 3 (remote/teleport, budget caps, sub-agents) | 2 (Google search, @ file inject) | 2 (LSP, sourcegraph) | 3 (MCP server, YAML workflows, replay/audit) |
| **Ties** | 7 | 7 | 7 | 7 |

---

## The Brutal Truth About aio

> [!CAUTION]
> This section is intentionally harsh. It's meant to be constructive, not discouraging.

### What aio Actually Is Right Now
aio is a **well-structured scaffold** — not a product. It has the skeleton of a real AI CLI (config, agent loop, tools, TUI, workflows), but compared to the other three:

1. **The TUI is fragile.** Raw curses with manual event handling. Claude Code uses Ink (React), Gemini CLI uses Ink, OpenCode uses BubbleTea. All three have battle-tested rendering frameworks. aio's TUI will break on edge cases (resize, Unicode, Windows terminal quirks) that these frameworks handle automatically.

2. **The agent loop is a mock.** The `AgentExecutor` has the right architecture (plan→act→observe→replan), but it's calling a basic LLM client that returns single completions. The other three tools have sophisticated agent loops with tool-calling APIs, function declarations, retry logic, and streaming tool results. aio's agent doesn't actually do agentic coding yet.

3. **The tool set is minimal.** 5 tool categories vs Claude Code's ~10, Gemini's 15, OpenCode's 13. Missing critical tools: web fetch, web search, code diagnostics, file editing (patch/diff), and ask-user.

4. **No MCP client.** aio can *expose* tools as an MCP server (unique), but it can't *consume* external MCP servers. Every competitor has MCP client support. This is a critical gap.

5. **No context/memory system.** No `CLAUDE.md` / `GEMINI.md` equivalent. No auto-memory. No context compression. This means the AI has no project-specific context persistence between sessions.

6. **No checkpointing or session management.** The `SessionStore` is append-only. No resume, no branching, no rewind. Claude Code and Gemini CLI let you save/resume/fork/rewind conversations — this is essential for real productivity.

7. **Provider support is narrow.** aio supports llama.cpp and OpenAI-compatible, which is good for local AI. But OpenCode supports 8 providers natively. aio's `\connect` presets are clever but limited.

8. **The safety system is coarse.** Three levels (off/confirm/strict) vs Claude Code's per-tool allow/deny lists with permission modes. Real users need granular control.

### What aio Does Better Than Everyone Else

These are real, defensible advantages:

| # | Feature | Why It Matters |
|:--|:--|:--|
| 1 | **MCP Server mode** | None of the other three can *expose* their tools for other AI clients. aio can. This is a real integration story. |
| 2 | **YAML Workflow Engine** | Declarative task pipelines with steps. Nobody else has this. |
| 3 | **Structured Audit/Replay** | `aio replay` with JSON audit logs. Better observability than any competitor. |
| 4 | **Markdown Side-Panel** | Dual-panel UX with raw/rendered toggle. Unique and genuinely useful. |
| 5 | **Local-first architecture** | Designed from day one for `localhost` AI servers. No cloud dependency. |
| 6 | **Python ecosystem** | Easier to extend for data science / ML workflows than TypeScript/Go. |

### Where aio Stands — Honest Tier Placement

```
Tier S: Claude Code        — The most complete, most polished, most integrated
Tier A: Gemini CLI         — Close second, stronger built-in tools and search
Tier B: OpenCode           — Best multi-provider, great TUI, but archived
Tier C: aio                — Good architecture, unique ideas, but far from production
```

---

## What to Adopt — Prioritized by Impact

### 🔴 Critical (Without These, aio Can't Compete)

| # | Feature | Source | Effort | Why Critical |
|:--|:--|:--|:--|:--|
| 1 | **MCP Client** | All 3 competitors | High | Can't use external tools (GitHub, Slack, DB) without it |
| 2 | **Project Context Files** (`.aio/context.md`) | CC/GC | Low | Zero project awareness between sessions |
| 3 | **Real Agent Loop** (function calling, tool use API) | CC/GC | High | Current loop is a structured mock — no real agentic coding |
| 4 | **@ File Injection** | GC | Low | Huge DX win, trivial to implement |
| 5 | **More Built-in Tools** (patch/diff file edit, web fetch, web search, diagnostics) | All 3 | Medium | Current 5 tools is simply not enough |

### 🟡 Important (Makes aio Usable for Real Work)

| # | Feature | Source | Effort | Why Important |
|:--|:--|:--|:--|:--|
| 6 | **Session Save/Resume/Fork** | CC/GC | Medium | Can't pause and resume complex tasks |
| 7 | **Context Compression** (`\compact`) | CC/GC/OC | Low | Sessions blow up token budgets |
| 8 | **Custom Commands** (MD files with args) | OC | Low | User shortcuts make daily use much faster |
| 9 | **Headless JSON/stream-JSON output** | CC/GC/OC | Low | CI/CD integration requires structured output |
| 10 | **Per-Tool Permissions** | CC | Medium | Coarse safety levels aren't enough |

### 🟢 Differentiator (Doubles Down on aio's Strengths)

| # | Feature | Source | Effort | Why |
|:--|:--|:--|:--|:--|
| 11 | **LSP Integration** | OC | High | Code-aware diagnostics — would be unique among Python CLIs |
| 12 | **Auto-Compact** | OC | Low | Automatic context management at 95% threshold |
| 13 | **Plan Mode** (read-only research) | CC/GC | Medium | Safer code exploration before making changes |
| 14 | **Sub-Agents** | CC | High | Already on P2 roadmap — CC's `--agents` is the gold standard |
| 15 | **Budget Caps** (`--max-budget-usd`) | CC | Low | Cost control for paid APIs |

---

## Conclusion

**aio has good bones.** The architecture (config system, tool registry, agent executor, workflow engine, MCP server) is well-designed. But right now it's a **foundation without a building on top**.

The three competitors are production tools used by thousands of developers daily. aio is a scaffold used by its creator.

**To become competitive, focus on items 1-5 above.** Specifically:
- An MCP client + project context files would immediately make aio feel like a real tool
- A real agent loop with function calling would be the difference between "CLI that calls an LLM" and "AI agent that codes"
- The YAML workflow engine + MCP server + local-first focus gives aio a **real niche**: the open, provider-agnostic, self-hostable AI coding agent

That niche is worth pursuing — none of the big three serve it well.
