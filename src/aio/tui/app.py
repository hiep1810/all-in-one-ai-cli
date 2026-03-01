from __future__ import annotations

import json
import shlex
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Header, Footer, Input, Markdown, RichLog, ContentSwitcher, TextArea, OptionList

from aio.agent.executor import AgentExecutor
from aio.agent.safety import should_block_tool
from aio.config.loader import config_to_dict, load_config, update_config
from aio.logging.audit import AuditLogger
from aio.memory.session_store import SessionStore
from aio.tools.registry import ToolRegistry
from aio.utils.errors import ToolValidationError
from aio.workflows.runner import run_workflow
from aio.llm.router import get_client
from aio.tui.command_palette import CommandPalette

HELP_TEXT = r"""Commands:
  \help
  \md open <path|url>
  \md stash
  \md clear
  \agent <goal> [--approve-risky]
  \chat <session> <message>
  \tool <name> [k=v ...] [--approve-risky]
  \tools
  \history
  \clear
  \save [path]
  \workflow <path>
  \replay <logfile>
  \config show
  \config set <key> <value>
  \exit
Main mode:
  Type any text without leading "\" to chat directly with AI.
"""

class AIOConsole(App):
    CSS = """
    AIOConsole {
        layers: base overlay;
    }
    #main-container {
        layout: horizontal;
        layer: base;
    }
    #chat-log {
        width: 1fr;
        height: 100%;
        border-right: solid green;
    }
    #md-view {
        width: 1fr;
        height: 100%;
        display: none;
        padding: 1;
    }
    #md-view.-visible {
        display: block;
    }
    #md-viewer, #md-editor {
        width: 100%;
        height: 100%;
    }
    #suggest-popup {
        layer: overlay;
        display: none;
        dock: bottom;
        margin-bottom: 3;
        width: 50%;
        max-width: 60;
        max-height: 8;
        background: $surface;
        border: solid $accent;
    }
    #suggest-popup.-visible {
        display: block;
    }
    #input {
        layer: base;
        dock: bottom;
        margin: 0;
        border: solid panel;
    }
    
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
    """
    
    BINDINGS = [
        ("ctrl+o", "toggle_markdown_focus", "Toggle Focus (Chat/MD)"),
        ("ctrl+l", "clear_log", "Clear Log"),
        ("ctrl+p", "open_palette", "Command Palette"),
        ("e", "toggle_edit_mode", "Edit MD"),
    ]

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.logger_audit = AuditLogger()
        self.store = SessionStore()
        self.registry = ToolRegistry()
        self.executor = AgentExecutor(self.config, self.registry)
        self.command_history: list[str] = []
        self._history_file = Path(".aio") / "tui_history.json"
        if self._history_file.exists():
            try:
                self.command_history = json.loads(self._history_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        self.last_response = ""
        self.pending_approval_raw: str | None = None
        self.current_md_path: Path | None = None
        self.history_index: int = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-container"):
            yield RichLog(id="chat-log", markup=True, highlight=True)
            with ContentSwitcher(initial="md-viewer", id="md-view"):
                yield Markdown(id="md-viewer")
                yield TextArea(id="md-editor", language="markdown")
        yield OptionList(id="suggest-popup")
        yield Input(placeholder="cmd> ", id="input")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "All-in-One Agent Console"
        self.sub_title = f"Provider: {self.config.model_provider} • Model: {self.config.model_name}"
        log = self.query_one("#chat-log", RichLog)
        log.write("[bold cyan]AIO Console ready.[/bold cyan] Chat directly, or use [yellow]\\help[/yellow] for commands.")
        inp = self.query_one("#input", Input)
        
        # Build suggester list
        base_cmds = [
            r"\help", r"\clear", r"\history", r"\tools", r"\save ", r"\exit",
            r"\chat ", r"\agent ", r"\workflow ", r"\config "
        ]
        md_cmds = [r"\md open ", r"\md stash", r"\md clear"]
        tool_cmds = [f"\\tool {t} " for t in self.registry.list_tools()]
        self.all_commands = base_cmds + md_cmds + tool_cmds
        
        inp.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        val = event.value
        popup = self.query_one("#suggest-popup", OptionList)
        
        if not val or not val.startswith("\\"):
            popup.remove_class("-visible")
            return
            
        matches = [c for c in self.all_commands if val.lower() in c.lower()]
        if not matches:
            popup.remove_class("-visible")
            return
            
        popup.clear_options()
        popup.add_options(matches)
        popup.highlighted = 0
        popup.add_class("-visible")

    def action_toggle_markdown_focus(self) -> None:
        md_view = self.query_one("#md-view", ContentSwitcher)
        inp = self.query_one("#input", Input)
        if inp.has_focus:
            if md_view.has_class("-visible"):
                if md_view.current == "md-viewer":
                    self.query_one("#md-viewer", Markdown).focus()
                else:
                    self.query_one("#md-editor", TextArea).focus()
        else:
            inp.focus()

    from textual import events
    
    def on_key(self, event: events.Key) -> None:
        inp = self.query_one("#input", Input)
        if not inp.has_focus:
            return
            
        popup = self.query_one("#suggest-popup", OptionList)
        if popup.has_class("-visible"):
            if event.key == "up":
                if popup.highlighted is not None and popup.highlighted > 0:
                    popup.highlighted -= 1
                event.prevent_default()
                return
            elif event.key == "down":
                if popup.highlighted is not None and popup.highlighted < popup.option_count - 1:
                    popup.highlighted += 1
                event.prevent_default()
                return
            elif event.key == "tab":
                if popup.highlighted is not None:
                    opt = popup.get_option_at_index(popup.highlighted)
                    inp.value = str(opt.prompt)
                    inp.cursor_position = len(inp.value)
                    popup.remove_class("-visible")
                event.prevent_default()
                return

        # Fallback to history navigating if popup not active or not intercepting
        if event.key == "up":
            if self.command_history and self.history_index > 0:
                self.history_index -= 1
                inp.value = self.command_history[self.history_index]
                inp.action_end()
                popup.remove_class("-visible")
            event.prevent_default()
            
        elif event.key == "down":
            if self.command_history and self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                inp.value = self.command_history[self.history_index]
                inp.action_end()
            elif self.history_index == len(self.command_history) - 1:
                self.history_index = len(self.command_history)
                inp.value = ""
            event.prevent_default()

    def action_clear_log(self) -> None:
        self.query_one("#chat-log", RichLog).clear()

    def action_open_palette(self) -> None:
        tools = self.registry.list_tools()
        def on_selected(command: str):
            if command:
                inp = self.query_one("#input", Input)
                inp.value = command
                inp.focus()
        self.push_screen(CommandPalette(tools), on_selected)

    def action_toggle_edit_mode(self) -> None:
        switcher = self.query_one("#md-view", ContentSwitcher)
        if not switcher.has_class("-visible"):
            return
            
        md_viewer = self.query_one("#md-viewer", Markdown)
        md_editor = self.query_one("#md-editor", TextArea)
        
        if switcher.current == "md-viewer":
            if self.current_md_path:
                md_editor.text = self.current_md_path.read_text(encoding="utf-8")
                switcher.current = "md-editor"
                md_editor.focus()
        else:
            if self.current_md_path:
                self.current_md_path.write_text(md_editor.text, encoding="utf-8")
                md_viewer.update(md_editor.text)
                switcher.current = "md-viewer"
                self.query_one("#input", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        inp = self.query_one("#input", Input)
        inp.value = ""
        popup = self.query_one("#suggest-popup", OptionList)
        popup.remove_class("-visible")
        log = self.query_one("#chat-log", RichLog)

        if not raw:
            return

        if self.pending_approval_raw is not None:
            log.write(f"> {raw}")
            answer = raw.lower()
            pending = self.pending_approval_raw
            self.pending_approval_raw = None
            if answer in {"y", "yes"}:
                approved = pending
                if "--approve-risky" not in approved:
                    approved += " --approve-risky"
                log.write(f"> {approved}")
                self._execute_line_sync(approved)
            else:
                log.write("[reset]Cancelled risky action.[/reset]")
            inp.placeholder = "cmd> "
            return

        log.write(f"> [bold]{raw}[/bold]")
        self.command_history.append(raw)
        self.history_index = len(self.command_history)
        self._history_file.parent.mkdir(parents=True, exist_ok=True)
        self._history_file.write_text(json.dumps(self.command_history[-100:]), encoding="utf-8")
        
        if raw.startswith("\\"):
            if raw.startswith("\\md"):
                self._handle_markdown_command(raw)
            else:
                self._execute_line_sync(raw)
        else:
            inp.disabled = True
            log.write("[italic green]ai thinking...[/italic green]")
            self._handle_chat_background(raw)

    def _handle_markdown_command(self, raw: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        md_viewer = self.query_one("#md-viewer", Markdown)
        md_view_container = self.query_one("#md-view", ContentSwitcher)
        
        try:
            tokens = shlex.split(raw[1:])
        except ValueError as exc:
            log.write(f"[red]Parse error:[/red] {exc}")
            return
            
        if not tokens or tokens[0] != "md":
            log.write("Usage: \\md open <path> | \\md stash | \\md clear")
            return

        if len(tokens) >= 2 and tokens[1] == "clear":
            md_view_container.remove_class("-visible")
            md_viewer.update("")
            self.current_md_path = None
            log.write("Markdown panel cleared.")
            return

        if len(tokens) >= 2 and tokens[1] == "stash":
            md_files = sorted([p for p in Path('.').rglob('*.md') if '.git' not in p.parts and '.venv' not in p.parts and '.aio' not in p.parts][:50])
            if not md_files:
                log.write("No markdown files found in current directory.")
                return
            stash_text = "# Markdown Stash\n\nUse `\\md open <path>` to view.\n\n"
            for f in md_files:
                stash_text += f"* `{f}`\n"
            md_viewer.update(stash_text)
            md_view_container.current = "md-viewer"
            md_view_container.add_class("-visible")
            self.current_md_path = None
            return

        if len(tokens) >= 3 and tokens[1] == "open":
            path_str = " ".join(tokens[2:])
            if path_str.startswith("http://") or path_str.startswith("https://"):
                try:
                    req = urllib.request.Request(path_str, headers={'User-Agent': 'aio-cli'})
                    with urllib.request.urlopen(req, timeout=5) as response:
                        text = response.read().decode('utf-8')
                    md_viewer.update(text)
                    md_view_container.current = "md-viewer"
                    md_view_container.add_class("-visible")
                    self.current_md_path = None
                    log.write(f"Markdown loaded from URL: {path_str}")
                except Exception as e:
                    log.write(f"[red]Failed to fetch {path_str}:[/red] {e}")
                return

            path = Path(path_str)
            if not path.exists() or not path.is_file():
                log.write(f"[red]Markdown file not found:[/red] {path}")
                return
            
            text = path.read_text(encoding="utf-8")
            md_viewer.update(text)
            md_view_container.current = "md-viewer"
            md_view_container.add_class("-visible")
            self.current_md_path = path
            log.write(f"Markdown loaded: {path}")
            return

        log.write("Usage: \\md open <path|url> | \\md stash | \\md clear")

    @work(exclusive=True, thread=True)
    def _handle_chat_background(self, prompt: str) -> None:
        client = get_client(self.config)
        try:
            result = client.complete(prompt)
            self.call_from_thread(self._on_chat_complete, prompt, str(result))
        except Exception as exc:
            self.call_from_thread(self._on_chat_error, str(exc))

    def _on_chat_complete(self, prompt: str, result: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        inp = self.query_one("#input", Input)
        self.last_response = result
        self.store.append("main", {"role": "user", "content": prompt})
        self.store.append("main", {"role": "assistant", "content": result})
        self.logger_audit.log({"cmd": "ask", "prompt": prompt, "via": "tui"})
        log.write(f"[cyan]ai>[/cyan] {result}")
        inp.disabled = False
        inp.focus()

    def _on_chat_error(self, error: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        inp = self.query_one("#input", Input)
        log.write(f"[red]ai> Error:[/red] {error}")
        inp.disabled = False
        inp.focus()

    def _execute_line_sync(self, raw: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        inp = self.query_one("#input", Input)
        
        command_line = raw[1:].strip()
        if not command_line:
            log.write("Use \\help to view commands.")
            return
            
        try:
            tokens = shlex.split(command_line)
        except ValueError as exc:
            log.write(f"Parse error: {exc}")
            return
            
        if not tokens:
            return

        cmd = tokens[0]

        if cmd in {"help", "?"}:
            log.write(HELP_TEXT.strip())
            return

        if cmd in {"exit", "quit"}:
            self.exit()
            return

        if cmd == "tools":
            log.write("\n".join(self.registry.list_tools()))
            return

        if cmd == "history":
            limit = 20
            if len(tokens) > 1:
                try:
                    limit = max(1, int(tokens[1]))
                except ValueError:
                    log.write("Usage: \\history [n]")
                    return
            recent = self.command_history[-limit:]
            if not recent:
                log.write("No history yet.")
            else:
                log.write("\n".join(f"{idx + 1}. {line}" for idx, line in enumerate(recent)))
            return

        if cmd == "clear":
            log.clear()
            return

        if cmd == "save":
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            out_path = Path(tokens[1]) if len(tokens) == 2 else Path(".aio/sessions") / f"tui-export-{stamp}.txt"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text("\n".join(self.command_history) + "\n", encoding="utf-8")
            log.write(f"Saved transcript to {out_path}")
            return

        if cmd == "agent":
            approve_risky = "--approve-risky" in tokens[1:]
            args = [t for t in tokens[1:] if t != "--approve-risky"]
            goal = " ".join(args).strip()
            if not goal:
                log.write("Usage: \\agent <goal> [--approve-risky]")
                return
            result = self.executor.run(goal, approve_risky=approve_risky)
            if isinstance(result, dict):
                reason = str(result.get("result", ""))
                if reason.startswith("Approval required for risky tool:"):
                    self.pending_approval_raw = raw
                    log.write(f"[yellow]{reason}[/yellow]")
                    log.write("Approve risky action? [y/N]")
                    inp.placeholder = "approval> "
                    return
            self.last_response = json.dumps(result, indent=2)
            self.logger_audit.log({"cmd": "agent.run", "goal": goal, "via": "tui"})
            log.write(self.last_response)
            return

        if cmd == "chat":
            if len(tokens) < 3:
                log.write("Usage: \\chat <session> <message>")
                return
            session = tokens[1]
            message = " ".join(tokens[2:])
            path = self.store.append(session, {"role": "user", "content": message})
            self.logger_audit.log({"cmd": "chat", "session": session, "via": "tui"})
            log.write(f"Saved to {path}")
            return

        if cmd == "tool":
            if len(tokens) < 2:
                log.write("Usage: \\tool <name> [k=v ...] [--approve-risky]")
                return
            name = tokens[1]
            kwargs: dict[str, str] = {}
            approve_risky = False
            for kv in tokens[2:]:
                if kv == "--approve-risky":
                    approve_risky = True
                    continue
                if "=" not in kv:
                    log.write(f"Invalid tool arg: {kv}. Expected k=v")
                    return
                k, v = kv.split("=", 1)
                kwargs[k] = v
            blocked, reason = should_block_tool(self.config.safety_level, name, approve_risky)
            if blocked:
                if reason.startswith("Approval required for risky tool:"):
                    self.pending_approval_raw = raw
                    log.write(f"[yellow]{reason}[/yellow]")
                    log.write("Approve risky action? [y/N]")
                    inp.placeholder = "approval> "
                else:
                    log.write(f"[red]{reason}[/red]")
                return
            try:
                out = self.registry.run(name, **kwargs)
                self.last_response = str(out)
                self.logger_audit.log({"cmd": "tool.run", "name": name, "via": "tui"})
                log.write(self.last_response)
            except ToolValidationError as exc:
                log.write(f"[red]{exc}[/red]")
            return

        if cmd == "workflow":
            if len(tokens) != 2:
                log.write("Usage: \\workflow <path>")
                return
            res = run_workflow(tokens[1])
            self.last_response = str(res)
            self.logger_audit.log({"cmd": "workflow.run", "path": tokens[1], "via": "tui"})
            log.write(self.last_response)
            return

        if cmd == "replay":
            if len(tokens) != 2:
                log.write("Usage: \\replay <logfile>")
                return
            log_path = Path(".aio/logs") / tokens[1]
            if log_path.exists():
                log.write(log_path.read_text(encoding="utf-8"))
            else:
                log.write(f"Log not found: {log_path}")
            return

        if cmd == "config":
            if len(tokens) < 2:
                log.write("Usage: \\config show | \\config set <key> <value>")
                return
            sub = tokens[1]
            if sub == "show":
                log.write(json.dumps(config_to_dict(self.config), indent=2))
                return
            if sub == "set" and len(tokens) >= 4:
                key = tokens[2]
                value = " ".join(tokens[3:])
                update_config(key, value)
                self.config = load_config()
                self.executor = AgentExecutor(self.config, self.registry)
                log.write(f"Updated {key}")
                self.sub_title = f"Provider: {self.config.model_provider} • Model: {self.config.model_name}"
                return
            log.write("Usage: \\config show | \\config set <key> <value>")
            return

        log.write(f"Unknown command: {cmd}. Type '\\help'")

def run_tui() -> int:
    app = AIOConsole()
    app.run()
    return 0
