from __future__ import annotations

import curses
import json
import shlex
import subprocess
import textwrap
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from shutil import which

from aio.agent.executor import AgentExecutor
from aio.config.loader import config_to_dict, load_config, update_config
from aio.logging.audit import AuditLogger
from aio.memory.session_store import SessionStore
from aio.tools.registry import ToolRegistry
from aio.workflows.runner import run_workflow

HELP_TEXT = """Commands:
  \\help
  \\agent <goal>
  \\chat <session> <message>
  \\tool <name> [k=v ...]
  \\tools
  \\history [n]
  \\clear
  \\save [path]
  \\copylast
  \\workflow <path>
  \\replay <logfile>
  \\config show
  \\config set <key> <value>
  \\exit
Main mode:
  Type any text without leading "\\" to chat directly with AI.
"""

CLEAR_SIGNAL = "[[AIO_CLEAR_SCREEN]]"


class ExitTUI(Exception):
    pass


@dataclass
class TUIContext:
    config: object
    logger: AuditLogger
    store: SessionStore
    registry: ToolRegistry
    executor: AgentExecutor
    command_history: list[str]
    last_response: str


class TerminalUI:
    def __init__(self, screen: curses.window):
        self.screen = screen
        self.input_buffer = ""
        self.lines: list[str] = []
        self.max_history = 400
        self.use_color = False
        self.theme_name = "neon"
        self.theme = self._theme_spec(self.theme_name)
        config = load_config()
        self.theme_name = self._normalize_theme(getattr(config, "tui_theme", "neon"))
        self.theme = self._theme_spec(self.theme_name)
        registry = ToolRegistry()
        self.ctx = TUIContext(
            config=config,
            logger=AuditLogger(),
            store=SessionStore(),
            registry=registry,
            executor=AgentExecutor(config, registry),
            command_history=[],
            last_response="",
        )

    def add_output(self, text: str) -> None:
        parts = text.splitlines() or [""]
        self.lines.extend(parts)
        if len(self.lines) > self.max_history:
            self.lines = self.lines[-self.max_history :]

    def run(self) -> int:
        curses.curs_set(1)
        self.screen.keypad(True)
        self._init_colors()
        self.add_output('AIO Console ready. Chat directly, or use \\help for commands.')
        while True:
            self.render()
            try:
                key = self.screen.get_wch()
            except curses.error:
                continue

            try:
                self.handle_key(key)
            except ExitTUI:
                return 0

    def handle_key(self, key: object) -> None:
        if key == "\n":
            raw = self.input_buffer.strip()
            if raw:
                self.add_output(f"> {raw}")
                output = execute_line(self.ctx, raw)
                if output == CLEAR_SIGNAL:
                    self.lines = []
                    self.add_output("Screen cleared.")
                else:
                    self.add_output(output)
            self.input_buffer = ""
            return

        if key in ("\x7f", "\b") or key == curses.KEY_BACKSPACE:
            self.input_buffer = self.input_buffer[:-1]
            return

        if key == curses.KEY_RESIZE:
            return

        if isinstance(key, str) and key.isprintable():
            self.input_buffer += key

    def _init_colors(self) -> None:
        if not curses.has_colors():
            self.use_color = False
            return
        curses.start_color()
        curses.use_default_colors()
        colors = self.theme["colors"]
        curses.init_pair(1, colors["logo_a"], -1)
        curses.init_pair(2, colors["logo_b"], -1)
        curses.init_pair(3, colors["status"], -1)
        curses.init_pair(4, colors["hint"], -1)
        curses.init_pair(5, colors["title"], -1)
        self.use_color = True

    def _style(self, pair: int, bold: bool = False) -> int:
        if not self.use_color:
            return curses.A_BOLD if bold else curses.A_NORMAL
        attr = curses.color_pair(pair)
        if bold:
            attr |= curses.A_BOLD
        return attr

    def _draw(self, y: int, x: int, text: str, width: int, attr: int = 0) -> None:
        try:
            self.screen.addnstr(y, x, text, max(0, width), attr)
        except curses.error:
            pass

    def _normalize_theme(self, raw: str) -> str:
        return raw if raw in {"neon", "minimal", "matrix"} else "neon"

    def _theme_spec(self, theme_name: str) -> dict[str, object]:
        if theme_name == "minimal":
            return {
                "logo": [
                    "  AIO CLI",
                    "  --------",
                ],
                "subtitle": "Minimal Console",
                "hint": "Clean mode. Use `help` and `exit`.",
                "divider": "=",
                "colors": {
                    "logo_a": curses.COLOR_WHITE,
                    "logo_b": curses.COLOR_CYAN,
                    "status": curses.COLOR_WHITE,
                    "hint": curses.COLOR_CYAN,
                    "title": curses.COLOR_WHITE,
                },
            }
        if theme_name == "matrix":
            return {
                "logo": [
                    "  __  __   _  _____ ___ ___",
                    " |  \\/  | /_\\|_   _| _ \\_ _|",
                    " | |\\/| |/ _ \\ | | |   /| | ",
                    " |_|  |_/_/ \\_\\|_| |_|_\\___|",
                ],
                "subtitle": "Matrix Console",
                "hint": "Green stream mode. Type `help`.",
                "divider": "#",
                "colors": {
                    "logo_a": curses.COLOR_GREEN,
                    "logo_b": curses.COLOR_BLACK,
                    "status": curses.COLOR_GREEN,
                    "hint": curses.COLOR_GREEN,
                    "title": curses.COLOR_GREEN,
                },
            }
        return {
            "logo": [
                "   ___    ___   ___     ___ _     ___ ",
                "  / _ |  / _ | / _ |   / __| |   |_ _|",
                " / __ | / __ |/ __ |  | (__| |__  | | ",
                "/_/ |_|/_/ |_/_/ |_|   \\___|____| |___|",
            ],
            "subtitle": "All-in-One Agent Console",
            "hint": "Chat by default. Use \\help for commands. Use \\exit to quit.",
            "divider": "-",
            "colors": {
                "logo_a": curses.COLOR_CYAN,
                "logo_b": curses.COLOR_BLUE,
                "status": curses.COLOR_GREEN,
                "hint": curses.COLOR_YELLOW,
                "title": curses.COLOR_MAGENTA,
            },
        }

    def render(self) -> None:
        configured_theme = self._normalize_theme(getattr(self.ctx.config, "tui_theme", "neon"))
        if configured_theme != self.theme_name:
            self.theme_name = configured_theme
            self.theme = self._theme_spec(self.theme_name)
            self._init_colors()

        self.screen.erase()
        height, width = self.screen.getmaxyx()
        header_lines = self.theme["logo"]
        subhead = str(self.theme["subtitle"])
        hint = str(self.theme["hint"])
        divider_char = str(self.theme["divider"])

        y = 0
        for idx, line in enumerate(header_lines):
            style = self._style(1 if idx % 2 == 0 else 2, bold=True)
            self._draw(y, 0, line[: max(0, width - 1)], width - 1, style)
            y += 1

        self._draw(y, 0, subhead, width - 1, self._style(5, bold=True))
        y += 1
        self._draw(y, 0, hint, width - 1, self._style(4))
        y += 1
        self._draw(y, 0, divider_char * max(1, width - 1), width - 1, self._style(2))
        y += 1

        bottom_reserved = 2
        output_height = max(1, height - y - bottom_reserved)

        wrapped: list[str] = []
        for line in self.lines:
            wrapped.extend(textwrap.wrap(line, width=max(10, width - 1)) or [""])

        visible = wrapped[-output_height:]
        for idx, line in enumerate(visible):
            self._draw(y + idx, 0, line, width - 1)

        status = (
            f" provider={self.ctx.config.model_provider}  "
            f"model={self.ctx.config.model_name}  "
            f"theme={self.theme_name}  "
            f"safety={self.ctx.config.safety_level} "
        )
        self._draw(height - 2, 0, status.ljust(max(0, width - 1)), width - 1, self._style(3))

        prompt = f" cmd> {self.input_buffer}"
        self._draw(height - 1, 0, prompt.ljust(max(0, width - 1)), width - 1, self._style(1, bold=True))
        self.screen.move(height - 1, min(len(prompt), max(0, width - 1)))
        self.screen.refresh()


def execute_line(ctx: TUIContext, raw: str) -> str:
    if not raw.strip():
        return ""
    ctx.command_history.append(raw.strip())

    if not raw.startswith("\\"):
        from aio.llm.router import get_client

        prompt = raw.strip()
        result = str(get_client(ctx.config).complete(prompt))
        ctx.last_response = result
        ctx.store.append("main", {"role": "user", "content": prompt})
        ctx.store.append("main", {"role": "assistant", "content": result})
        ctx.logger.log({"cmd": "ask", "prompt": prompt, "via": "tui"})
        return result

    command_line = raw[1:].strip()
    if not command_line:
        return "Use \\help to view commands."
    try:
        tokens = shlex.split(command_line)
    except ValueError as exc:
        return f"Parse error: {exc}"
    if not tokens:
        return "Use \\help to view commands."

    cmd = tokens[0]

    if cmd in {"help", "?"}:
        return HELP_TEXT.strip()

    if cmd in {"exit", "quit"}:
        raise ExitTUI

    if cmd == "tools":
        return "\n".join(ctx.registry.list_tools())

    if cmd == "history":
        limit = 20
        if len(tokens) > 1:
            try:
                limit = max(1, int(tokens[1]))
            except ValueError:
                return "Usage: \\history [n]"
        recent = ctx.command_history[-limit:]
        if not recent:
            return "No history yet."
        return "\n".join(f"{idx + 1}. {line}" for idx, line in enumerate(recent))

    if cmd == "clear":
        return CLEAR_SIGNAL

    if cmd == "save":
        if len(tokens) > 2:
            return "Usage: \\save [path]"
        if len(tokens) == 2:
            out_path = Path(tokens[1])
        else:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            out_path = Path(".aio/sessions") / f"tui-export-{stamp}.txt"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        transcript = "\n".join(ctx.command_history) + "\n"
        out_path.write_text(transcript, encoding="utf-8")
        return f"Saved transcript to {out_path}"

    if cmd == "copylast":
        if not ctx.last_response:
            return "No AI response to copy yet."
        copied = _copy_to_clipboard(ctx.last_response)
        if copied:
            return "Copied last AI response to clipboard."
        return "Clipboard tool not found. Last response kept in memory."

    if cmd == "agent":
        goal = " ".join(tokens[1:]).strip()
        if not goal:
            return "Usage: \\agent <goal>"
        result = ctx.executor.run(goal)
        ctx.last_response = json.dumps(result, indent=2)
        ctx.logger.log({"cmd": "agent.run", "goal": goal, "via": "tui"})
        return ctx.last_response

    if cmd == "chat":
        if len(tokens) < 3:
            return "Usage: \\chat <session> <message>"
        session = tokens[1]
        message = " ".join(tokens[2:])
        path = ctx.store.append(session, {"role": "user", "content": message})
        ctx.logger.log({"cmd": "chat", "session": session, "via": "tui"})
        return f"Saved to {path}"

    if cmd == "tool":
        if len(tokens) < 2:
            return "Usage: \\tool <name> [k=v ...]"
        name = tokens[1]
        kwargs: dict[str, str] = {}
        for kv in tokens[2:]:
            if "=" not in kv:
                return f"Invalid tool arg: {kv}. Expected k=v"
            k, v = kv.split("=", 1)
            kwargs[k] = v
        result = ctx.registry.run(name, **kwargs)
        ctx.last_response = str(result)
        ctx.logger.log({"cmd": "tool.run", "name": name, "via": "tui"})
        return ctx.last_response

    if cmd == "workflow":
        if len(tokens) != 2:
            return "Usage: \\workflow <path>"
        result = run_workflow(tokens[1])
        ctx.last_response = str(result)
        ctx.logger.log({"cmd": "workflow.run", "path": tokens[1], "via": "tui"})
        return ctx.last_response

    if cmd == "replay":
        if len(tokens) != 2:
            return "Usage: \\replay <logfile>"
        log_path = Path(".aio/logs") / tokens[1]
        return log_path.read_text(encoding="utf-8")

    if cmd == "config":
        if len(tokens) < 2:
            return "Usage: \\config show | \\config set <key> <value>"
        sub = tokens[1]
        if sub == "show":
            return json.dumps(config_to_dict(ctx.config), indent=2)
        if sub == "set" and len(tokens) >= 4:
            key = tokens[2]
            value = " ".join(tokens[3:])
            update_config(key, value)
            ctx.config = load_config()
            ctx.executor = AgentExecutor(ctx.config, ctx.registry)
            return f"Updated {key}"
        return "Usage: \\config show | \\config set <key> <value>"

    return f"Unknown command: {cmd}. Type '\\help'"


def _copy_to_clipboard(text: str) -> bool:
    commands = [
        ["pbcopy"],
        ["wl-copy"],
        ["xclip", "-selection", "clipboard"],
    ]
    for cmd in commands:
        if which(cmd[0]) is None:
            continue
        try:
            subprocess.run(cmd, input=text, text=True, check=True, capture_output=True)
            return True
        except Exception:
            continue
    return False


def run_tui() -> int:
    def _wrapped(screen: curses.window) -> int:
        app = TerminalUI(screen)
        return app.run()

    return curses.wrapper(_wrapped)
