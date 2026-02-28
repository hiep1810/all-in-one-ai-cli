from __future__ import annotations

import curses
import json
from os.path import commonprefix
import shlex
import subprocess
import textwrap
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from shutil import which

from aio.agent.executor import AgentExecutor
from aio.agent.safety import should_block_tool
from aio.config.loader import config_to_dict, load_config, update_config
from aio.logging.audit import AuditLogger
from aio.memory.session_store import SessionStore
from aio.tools.registry import ToolRegistry
from aio.utils.errors import ToolValidationError
from aio.workflows.runner import run_workflow

HELP_TEXT = r"""Commands:
  \help
  \md open <path>
  \md mode <raw|rendered>
  \md focus <input|markdown>
  \md clear
  \agent <goal> [--approve-risky]
  \chat <session> <message>
  \tool <name> [k=v ...] [--approve-risky]
  \tools
  \history [n]
  \clear
  \save [path]
  \copylast
  \workflow <path>
  \replay <logfile>
  \config show
  \config set <key> <value>
  \exit
Main mode:
  Type any text without leading "\" to chat directly with AI.
"""

CLEAR_SIGNAL = "[[AIO_CLEAR_SCREEN]]"
SLASH_COMMANDS = [
    "help",
    "md",
    "agent",
    "chat",
    "tool",
    "tools",
    "history",
    "clear",
    "save",
    "copylast",
    "workflow",
    "replay",
    "config",
    "exit",
]
APPROVAL_REQUIRED_PREFIX = "Approval required for risky tool:"
CONFIG_KEYS = [
    "model_provider",
    "model_name",
    "model_base_url",
    "model_timeout_seconds",
    "tui_theme",
    "safety_level",
]
CONFIG_VALUE_HINTS: dict[str, list[str]] = {
    "model_provider": ["mock", "llama_cpp"],
    "tui_theme": ["neon", "minimal", "matrix"],
    "safety_level": ["off", "confirm", "strict"],
}


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
        self.cursor_pos = 0
        self.selection_mode = False
        self.selection_anchor: int | None = None
        self.selection_cursor: int | None = None
        self.markdown_path: str | None = None
        self.markdown_raw_text = ""
        self.markdown_mode = "rendered"
        self.markdown_scroll = 0
        self.focus_target = "input"  # input | markdown
        self.history_nav_index: int | None = None
        self.history_nav_draft = ""
        self.reverse_search_index: int | None = None
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
        self.pending_approval_raw: str | None = None

    def add_output(self, text: str) -> None:
        parts = text.splitlines() or [""]
        self.lines.extend(parts)
        if len(self.lines) > self.max_history:
            self.lines = self.lines[-self.max_history :]

    def run(self) -> int:
        curses.curs_set(1)
        self.screen.keypad(True)
        try:
            curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
        except curses.error:
            pass
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
        if _is_ctrl(key, 15):  # Ctrl+O
            if not self.markdown_path:
                self.add_output("Open markdown first with \\md open <path>.")
                return
            self.focus_target = toggle_focus(self.focus_target)
            self.add_output(f"Focus: {self.focus_target}")
            return

        if _is_ctrl(key, 19):  # Ctrl+S
            self._toggle_selection_mode()
            return

        if self.selection_mode:
            self._handle_selection_key(key)
            return

        if self.focus_target == "markdown" and self.markdown_path is not None:
            if key in {curses.KEY_NPAGE, curses.KEY_DOWN}:
                self.markdown_scroll += 3 if key == curses.KEY_DOWN else 12
                return
            if key in {curses.KEY_PPAGE, curses.KEY_UP}:
                self.markdown_scroll -= 3 if key == curses.KEY_UP else 12
                return

        if _is_ctrl(key, 3):  # Ctrl+C
            self.pending_approval_raw, self.reverse_search_index, self.history_nav_index, self.history_nav_draft = (
                reset_input_state("")
            )
            self.input_buffer = ""
            self.cursor_pos = 0
            self.add_output("Input cancelled.")
            return

        if _is_ctrl(key, 11):  # Ctrl+K
            self.input_buffer, self.cursor_pos = clear_to_line_end(self.input_buffer, self.cursor_pos)
            return

        if _is_ctrl(key, 21):  # Ctrl+U
            self.input_buffer, self.cursor_pos = clear_to_line_start(self.input_buffer, self.cursor_pos)
            return

        if _is_ctrl(key, 23):  # Ctrl+W
            self.input_buffer, self.cursor_pos = delete_prev_word(self.input_buffer, self.cursor_pos)
            return

        if key == "\x1b":  # Esc
            self.pending_approval_raw, self.reverse_search_index, self.history_nav_index, self.history_nav_draft = (
                reset_input_state(self.input_buffer)
            )
            self.cursor_pos = len(self.input_buffer)
            self.add_output("Input state reset.")
            return

        if key == "\n":
            raw = self.input_buffer.strip()
            if raw:
                if self.pending_approval_raw is not None:
                    self._handle_approval_response(raw)
                    self.input_buffer = ""
                    self.cursor_pos = 0
                    return
                self.add_output(f"> {raw}")
                if raw.startswith("\\"):
                    if raw.startswith("\\md"):
                        self.ctx.command_history.append(raw.strip())
                        self.add_output(self._handle_markdown_command(raw))
                    else:
                        output = execute_line(self.ctx, raw)
                        if output == CLEAR_SIGNAL:
                            self.lines = []
                            self.add_output("Screen cleared.")
                        elif _requires_approval(output):
                            self.pending_approval_raw = raw
                            self.add_output(output)
                            self.add_output("Approve risky action? [y/N]")
                        else:
                            self.add_output(output)
                else:
                    self._handle_chat_input(raw)
            self.input_buffer = ""
            self.cursor_pos = 0
            self.history_nav_index = None
            self.history_nav_draft = ""
            self.reverse_search_index = None
            return

        if _is_ctrl(key, 12):  # Ctrl+L
            self.lines = []
            self.add_output("Screen cleared.")
            self.reverse_search_index = None
            return

        if _is_ctrl(key, 18):  # Ctrl+R
            self._reverse_search_prev()
            return

        if key in ("\x7f", "\b") or key == curses.KEY_BACKSPACE:
            self.input_buffer, self.cursor_pos = delete_backspace(self.input_buffer, self.cursor_pos)
            self.reverse_search_index = None
            return

        if key == "\t":
            self.input_buffer = complete_input(self.input_buffer, self.ctx.registry.list_tools())
            self.cursor_pos = len(self.input_buffer)
            self.reverse_search_index = None
            return

        if key == curses.KEY_RESIZE:
            return

        if key == curses.KEY_MOUSE:
            self._handle_mouse_click()
            return

        if key == curses.KEY_LEFT:
            self.cursor_pos = max(0, self.cursor_pos - 1)
            return

        if key == curses.KEY_RIGHT:
            self.cursor_pos = min(len(self.input_buffer), self.cursor_pos + 1)
            return

        if key == curses.KEY_DC:
            self.input_buffer, self.cursor_pos = delete_forward(self.input_buffer, self.cursor_pos)
            return

        if key == curses.KEY_HOME or key == "\x01":  # Home or Ctrl+A
            self.cursor_pos = 0
            return

        if key == curses.KEY_END or key == "\x05":  # End or Ctrl+E
            self.cursor_pos = len(self.input_buffer)
            return

        if key == curses.KEY_UP:
            self._history_prev()
            self.reverse_search_index = None
            return

        if key == curses.KEY_DOWN:
            self._history_next()
            self.reverse_search_index = None
            return

        if isinstance(key, str) and key.isprintable():
            self.input_buffer, self.cursor_pos = insert_text(self.input_buffer, self.cursor_pos, key)
            self.reverse_search_index = None

    def _toggle_selection_mode(self) -> None:
        if self.selection_mode:
            self.selection_mode = False
            self.selection_anchor = None
            self.selection_cursor = None
            self.add_output("Selection mode off.")
            return
        if not self.lines:
            self.add_output("No output lines to select.")
            return
        self.selection_mode = True
        self.selection_anchor = len(self.lines) - 1
        self.selection_cursor = len(self.lines) - 1
        self.add_output("Selection mode on. Use Up/Down and Ctrl+Y to copy.")

    def _handle_selection_key(self, key: object) -> None:
        if key == "\x1b":  # Esc
            self.selection_mode = False
            self.selection_anchor = None
            self.selection_cursor = None
            self.add_output("Selection mode off.")
            return
        if key == curses.KEY_UP and self.selection_cursor is not None:
            self.selection_cursor = max(0, self.selection_cursor - 1)
            return
        if key == curses.KEY_DOWN and self.selection_cursor is not None:
            self.selection_cursor = min(len(self.lines) - 1, self.selection_cursor + 1)
            return
        if key == "\x19":  # Ctrl+Y
            text = selection_text(self.lines, self.selection_anchor, self.selection_cursor)
            if not text:
                self.add_output("No selection to copy.")
            elif _copy_to_clipboard(text):
                self.add_output("Copied selected lines to clipboard.")
            else:
                self.add_output("Clipboard tool not found. Selection not copied.")
            return

    def _history_prev(self) -> None:
        self.history_nav_index, self.history_nav_draft, self.input_buffer = history_prev(
            history=self.ctx.command_history,
            history_nav_index=self.history_nav_index,
            history_nav_draft=self.history_nav_draft,
            input_buffer=self.input_buffer,
        )
        self.cursor_pos = len(self.input_buffer)

    def _history_next(self) -> None:
        self.history_nav_index, self.history_nav_draft, self.input_buffer = history_next(
            history=self.ctx.command_history,
            history_nav_index=self.history_nav_index,
            history_nav_draft=self.history_nav_draft,
            input_buffer=self.input_buffer,
        )
        self.cursor_pos = len(self.input_buffer)

    def _reverse_search_prev(self) -> None:
        query = self.input_buffer.strip()
        index, match = reverse_search_prev(
            history=self.ctx.command_history,
            query=query,
            start_index=self.reverse_search_index,
        )
        if index is None or match is None:
            return
        self.reverse_search_index = index - 1
        self.input_buffer = match
        self.cursor_pos = len(match)

    def _handle_mouse_click(self) -> None:
        try:
            _, mouse_x, mouse_y, _, _ = curses.getmouse()
        except curses.error:
            return
        height, _ = self.screen.getmaxyx()
        input_y = max(0, height - 1)
        if mouse_y != input_y:
            return
        self.cursor_pos = cursor_from_click(
            mouse_x=mouse_x,
            prompt_prefix_len=len(" cmd> "),
            input_len=len(self.input_buffer),
        )

    def _handle_markdown_command(self, raw: str) -> str:
        try:
            tokens = shlex.split(raw[1:])
        except ValueError as exc:
            return f"Parse error: {exc}"
        if not tokens or tokens[0] != "md":
            return "Usage: \\md open <path> | \\md mode <raw|rendered> | \\md clear"

        if len(tokens) >= 2 and tokens[1] == "clear":
            self.markdown_path = None
            self.markdown_raw_text = ""
            self.markdown_scroll = 0
            if self.focus_target == "markdown":
                self.focus_target = "input"
            return "Markdown panel cleared."

        if len(tokens) >= 3 and tokens[1] == "focus":
            mode = tokens[2].strip().lower()
            if mode not in {"input", "markdown"}:
                return "Invalid focus. Use: input | markdown"
            if mode == "markdown" and not self.markdown_path:
                return "Open a markdown file first with \\md open <path>"
            self.focus_target = mode
            return f"Markdown focus set: {mode}"

        if len(tokens) >= 3 and tokens[1] == "mode":
            mode = tokens[2].strip().lower()
            if mode not in {"raw", "rendered"}:
                return "Invalid mode. Use: raw | rendered"
            self.markdown_mode = mode
            return f"Markdown mode set: {mode}"

        if len(tokens) >= 3 and tokens[1] == "open":
            path = Path(" ".join(tokens[2:]))
            if not path.exists() or not path.is_file():
                return f"Markdown file not found: {path}"
            text = path.read_text(encoding="utf-8")
            self.markdown_path = str(path)
            self.markdown_raw_text = text
            self.markdown_scroll = 0
            return f"Markdown loaded: {path}"

        return "Usage: \\md open <path> | \\md mode <raw|rendered> | \\md clear"

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
        markdown_panel_lines = markdown_display_lines(self.markdown_raw_text, self.markdown_mode)
        split_markdown = bool(markdown_panel_lines) and width >= 80
        left_width = width if not split_markdown else max(30, (width * 3 // 5))
        right_x = left_width + 1
        right_width = max(0, width - right_x)
        header_lines = self.theme["logo"]
        subhead = str(self.theme["subtitle"])
        hint = str(self.theme["hint"])
        divider_char = str(self.theme["divider"])

        y = 0
        for idx, line in enumerate(header_lines):
            style = self._style(1 if idx % 2 == 0 else 2, bold=True)
            self._draw(y, 0, line[: max(0, left_width - 1)], left_width - 1, style)
            y += 1

        self._draw(y, 0, subhead, left_width - 1, self._style(5, bold=True))
        y += 1
        self._draw(y, 0, hint, left_width - 1, self._style(4))
        y += 1
        self._draw(y, 0, divider_char * max(1, left_width - 1), left_width - 1, self._style(2))
        y += 1

        bottom_reserved = 3
        output_height = max(1, height - y - bottom_reserved)

        wrapped: list[tuple[int, str]] = []
        for src_idx, line in enumerate(self.lines):
            parts = textwrap.wrap(line, width=max(10, left_width - 1)) or [""]
            for part in parts:
                wrapped.append((src_idx, part))

        visible = wrapped[-output_height:]
        sel_range = selected_line_range(self.selection_anchor, self.selection_cursor, len(self.lines))
        for idx, (src_idx, line) in enumerate(visible):
            attr = 0
            if sel_range is not None and sel_range[0] <= src_idx <= sel_range[1]:
                attr = self._style(4, bold=True) | curses.A_REVERSE
            self._draw(y + idx, 0, line, left_width - 1, attr)

        if split_markdown and right_width > 8:
            for row in range(y - 1, height - 1):
                self._draw(row, left_width, "│", 1, self._style(2))
            md_title = f" MARKDOWN [{self.markdown_mode.upper()}] "
            if self.markdown_path is not None:
                md_title = f" MARKDOWN [{self.markdown_mode.upper()}] {Path(self.markdown_path).name} "
            self._draw(
                y - 1,
                right_x,
                md_title.ljust(max(1, right_width - 1)),
                right_width - 1,
                self._style(5, bold=True) | curses.A_REVERSE,
            )
            wrapped_md: list[str] = []
            for line in markdown_panel_lines:
                wrapped_md.extend(textwrap.wrap(line, width=max(8, right_width - 1)) or [""])
            self.markdown_scroll = clamp_scroll(self.markdown_scroll, len(wrapped_md), output_height)
            start = self.markdown_scroll
            end = min(len(wrapped_md), start + output_height)
            md_visible = wrapped_md[start:end]
            for idx, line in enumerate(md_visible):
                self._draw(y + idx, right_x, line, right_width - 1, self._style(4))

        if self.pending_approval_raw is not None:
            hint_text = "approval> type y/yes to approve, anything else to cancel"
        elif self.selection_mode:
            hint_text = "selection> Up/Down to select, Ctrl+Y copy, Esc exit"
        elif self.markdown_path is not None and self.focus_target == "markdown":
            hint_text = "markdown focus> Up/Down line scroll, PgUp/PgDn page, Ctrl+O switch"
        elif self.markdown_path is not None:
            hint_text = "input focus> Ctrl+O to control markdown panel"
        else:
            suggestions = suggest_input(self.input_buffer, self.ctx.registry.list_tools())
            hint_text = f"hints> {', '.join(suggestions)}" if suggestions else "hints> (none)"
        self._draw(height - 3, 0, hint_text.ljust(max(0, width - 1)), width - 1, self._style(4))

        status = (
            f" provider={self.ctx.config.model_provider}  "
            f"model={self.ctx.config.model_name}  "
            f"theme={self.theme_name}  "
            f"focus={self.focus_target}  "
            f"safety={self.ctx.config.safety_level} "
        )
        self._draw(height - 2, 0, status.ljust(max(0, width - 1)), width - 1, self._style(3))

        prompt = f" cmd> {self.input_buffer}"
        self._draw(height - 1, 0, prompt.ljust(max(0, width - 1)), width - 1, self._style(1, bold=True))
        cursor_x = len(" cmd> ") + self.cursor_pos
        self.screen.move(height - 1, min(cursor_x, max(0, width - 1)))
        self.screen.refresh()

    def _handle_chat_input(self, raw: str) -> None:
        from aio.llm.router import get_client

        prompt = raw.strip()
        self.ctx.command_history.append(prompt)
        client = get_client(self.ctx.config)
        buffer = ""
        previous_preview_count = 0
        try:
            for chunk in client.stream_complete(prompt):
                buffer += chunk
                preview_lines = [f"ai> {line}" for line in (buffer.splitlines() or [""])]
                if previous_preview_count > 0:
                    self.lines = self.lines[:-previous_preview_count]
                self.lines.extend(preview_lines)
                previous_preview_count = len(preview_lines)
                self.render()
        except Exception as exc:
            self.add_output(f"ai> Error: {exc}")
            return
        self.ctx.last_response = buffer
        self.ctx.store.append("main", {"role": "user", "content": prompt})
        self.ctx.store.append("main", {"role": "assistant", "content": buffer})
        self.ctx.logger.log({"cmd": "ask", "prompt": prompt, "via": "tui"})

    def _handle_approval_response(self, raw: str) -> None:
        answer = raw.strip().lower()
        self.add_output(f"> {raw}")
        pending = self.pending_approval_raw
        self.pending_approval_raw = None
        if pending is None:
            return
        if answer in {"y", "yes"}:
            approved = _inject_approve_flag(pending)
            self.add_output(f"> {approved}")
            output = execute_line(self.ctx, approved)
            self.add_output(output)
            return
        self.add_output("Cancelled risky action.")


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
        approve_risky = "--approve-risky" in tokens[1:]
        args = [t for t in tokens[1:] if t != "--approve-risky"]
        goal = " ".join(args).strip()
        if not goal:
            return "Usage: \\agent <goal> [--approve-risky]"
        result = ctx.executor.run(goal, approve_risky=approve_risky)
        if isinstance(result, dict):
            reason = str(result.get("result", ""))
            if _requires_approval(reason):
                return reason
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
            return "Usage: \\tool <name> [k=v ...] [--approve-risky]"
        name = tokens[1]
        kwargs: dict[str, str] = {}
        approve_risky = False
        for kv in tokens[2:]:
            if kv == "--approve-risky":
                approve_risky = True
                continue
            if "=" not in kv:
                return f"Invalid tool arg: {kv}. Expected k=v"
            k, v = kv.split("=", 1)
            kwargs[k] = v
        blocked, reason = should_block_tool(ctx.config.safety_level, name, approve_risky)
        if blocked:
            return reason
        try:
            result = ctx.registry.run(name, **kwargs)
        except ToolValidationError as exc:
            return str(exc)
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


def complete_slash_command(buffer: str) -> str:
    if not buffer.startswith("\\"):
        return buffer
    body = buffer[1:]
    if " " in body:
        return buffer

    matches = [cmd for cmd in SLASH_COMMANDS if cmd.startswith(body)]
    if not matches:
        return buffer
    if len(matches) == 1:
        return "\\" + matches[0] + " "

    shared = commonprefix(matches)
    if len(shared) > len(body):
        return "\\" + shared
    return buffer


def complete_input(buffer: str, tool_names: list[str]) -> str:
    if not buffer.startswith("\\"):
        return buffer
    body = buffer[1:]
    if body == "":
        return buffer
    if " " not in body:
        return complete_slash_command(buffer)

    try:
        parts = shlex.split(body)
    except ValueError:
        return buffer
    if not parts:
        return buffer

    cmd = parts[0]
    trailing_space = body.endswith(" ")

    if cmd == "tool":
        if len(parts) == 1:
            return _complete_token(buffer, body, "", tool_names)
        if len(parts) == 2 and not trailing_space:
            return _complete_token(buffer, body, parts[1], tool_names)
        return buffer

    if cmd == "md":
        if len(parts) == 1:
            return _complete_token(buffer, body, "", ["open", "mode", "focus", "clear"])
        if len(parts) == 2 and not trailing_space:
            return _complete_token(buffer, body, parts[1], ["open", "mode", "focus", "clear"])
        if len(parts) == 3 and parts[1] == "mode" and not trailing_space:
            return _complete_token(buffer, body, parts[2], ["raw", "rendered"])
        if len(parts) == 3 and parts[1] == "focus" and not trailing_space:
            return _complete_token(buffer, body, parts[2], ["input", "markdown"])
        return buffer

    if cmd == "config":
        if len(parts) == 1:
            return _complete_token(buffer, body, "", ["show", "set"])
        if len(parts) == 2 and not trailing_space:
            return _complete_token(buffer, body, parts[1], ["show", "set"])
        if len(parts) == 3 and parts[1] == "set" and not trailing_space:
            return _complete_token(buffer, body, parts[2], CONFIG_KEYS)
        if len(parts) == 4 and parts[1] == "set":
            key = parts[2]
            hints = CONFIG_VALUE_HINTS.get(key, [])
            if trailing_space:
                return buffer
            return _complete_token(buffer, body, parts[3], hints)
        return buffer

    return buffer


def suggest_input(buffer: str, tool_names: list[str], limit: int = 4) -> list[str]:
    if not buffer.startswith("\\"):
        return []
    body = buffer[1:]
    if body == "":
        return SLASH_COMMANDS[:limit]
    if " " not in body:
        return _match_candidates(body, SLASH_COMMANDS)[:limit]

    try:
        parts = shlex.split(body)
    except ValueError:
        return []
    if not parts:
        return []

    cmd = parts[0]
    trailing_space = body.endswith(" ")

    if cmd == "tool":
        if len(parts) == 1 and trailing_space:
            return tool_names[:limit]
        if len(parts) == 2 and not trailing_space:
            return _match_candidates(parts[1], tool_names)[:limit]
        return []

    if cmd == "md":
        if len(parts) == 1 and trailing_space:
            return ["open", "mode", "focus", "clear"][:limit]
        if len(parts) == 2 and not trailing_space:
            return _match_candidates(parts[1], ["open", "mode", "focus", "clear"])[:limit]
        if len(parts) == 2 and trailing_space and parts[1] == "mode":
            return ["raw", "rendered"][:limit]
        if len(parts) == 3 and parts[1] == "mode" and not trailing_space:
            return _match_candidates(parts[2], ["raw", "rendered"])[:limit]
        if len(parts) == 2 and trailing_space and parts[1] == "focus":
            return ["input", "markdown"][:limit]
        if len(parts) == 3 and parts[1] == "focus" and not trailing_space:
            return _match_candidates(parts[2], ["input", "markdown"])[:limit]
        return []

    if cmd == "config":
        if len(parts) == 1 and trailing_space:
            return ["show", "set"][:limit]
        if len(parts) == 2 and not trailing_space:
            return _match_candidates(parts[1], ["show", "set"])[:limit]
        if len(parts) == 2 and trailing_space and parts[1] == "set":
            return CONFIG_KEYS[:limit]
        if len(parts) == 3 and parts[1] == "set" and not trailing_space:
            return _match_candidates(parts[2], CONFIG_KEYS)[:limit]
        if len(parts) == 3 and parts[1] == "set" and trailing_space:
            return CONFIG_VALUE_HINTS.get(parts[2], [])[:limit]
        if len(parts) == 4 and parts[1] == "set" and not trailing_space:
            return _match_candidates(parts[3], CONFIG_VALUE_HINTS.get(parts[2], []))[:limit]
        return []

    return []


def _match_candidates(prefix: str, candidates: list[str]) -> list[str]:
    return [item for item in candidates if item.startswith(prefix)]


def _is_ctrl(key: object, code: int) -> bool:
    return key == chr(code) or key == code


def history_prev(
    history: list[str],
    history_nav_index: int | None,
    history_nav_draft: str,
    input_buffer: str,
) -> tuple[int | None, str, str]:
    if not history:
        return history_nav_index, history_nav_draft, input_buffer
    if history_nav_index is None:
        history_nav_draft = input_buffer
        history_nav_index = len(history) - 1
    elif history_nav_index > 0:
        history_nav_index -= 1
    return history_nav_index, history_nav_draft, history[history_nav_index]


def history_next(
    history: list[str],
    history_nav_index: int | None,
    history_nav_draft: str,
    input_buffer: str,
) -> tuple[int | None, str, str]:
    if not history or history_nav_index is None:
        return history_nav_index, history_nav_draft, input_buffer
    if history_nav_index < len(history) - 1:
        history_nav_index += 1
        return history_nav_index, history_nav_draft, history[history_nav_index]
    return None, history_nav_draft, history_nav_draft


def reverse_search_prev(
    history: list[str],
    query: str,
    start_index: int | None,
) -> tuple[int | None, str | None]:
    if not history:
        return None, None
    idx = len(history) - 1 if start_index is None else min(start_index, len(history) - 1)
    needle = query.lower()
    while idx >= 0:
        item = history[idx]
        if not needle or needle in item.lower():
            return idx, item
        idx -= 1
    return None, None


def selected_line_range(
    anchor: int | None,
    cursor: int | None,
    total_lines: int,
) -> tuple[int, int] | None:
    if anchor is None or cursor is None or total_lines <= 0:
        return None
    a = max(0, min(anchor, total_lines - 1))
    c = max(0, min(cursor, total_lines - 1))
    return (min(a, c), max(a, c))


def selection_text(lines: list[str], anchor: int | None, cursor: int | None) -> str:
    sel_range = selected_line_range(anchor, cursor, len(lines))
    if sel_range is None:
        return ""
    start, end = sel_range
    return "\n".join(lines[start : end + 1])


def toggle_focus(current: str) -> str:
    return "markdown" if current == "input" else "input"


def clamp_scroll(scroll: int, total: int, window: int) -> int:
    if total <= 0 or window <= 0:
        return 0
    max_scroll = max(0, total - window)
    return max(0, min(scroll, max_scroll))


def markdown_display_lines(raw_text: str, mode: str) -> list[str]:
    if not raw_text:
        return []
    if mode == "raw":
        return raw_text.splitlines()
    return render_markdown_lines(raw_text)


def cursor_from_click(mouse_x: int, prompt_prefix_len: int, input_len: int) -> int:
    raw = mouse_x - prompt_prefix_len
    return max(0, min(raw, input_len))


def render_markdown_lines(text: str) -> list[str]:
    lines: list[str] = []
    in_code = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            lines.append(f"  {line}")
            continue
        stripped = line.lstrip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            title = stripped.lstrip("#").strip().upper()
            if title:
                if level <= 1:
                    banner = "=" * max(14, min(60, len(title) + 10))
                    lines.append(banner)
                    lines.append(f"==  {title}  ==")
                    lines.append(banner)
                elif level == 2:
                    lines.append(f"-- {title} --")
                else:
                    lines.append(f"[{title}]")
            continue
        if stripped.startswith("- ") or stripped.startswith("* "):
            lines.append(f"• {stripped[2:].strip()}")
            continue
        if stripped.startswith("> "):
            lines.append(f"| {stripped[2:].strip()}")
            continue
        lines.append(stripped)
    return lines


def reset_input_state(input_buffer: str) -> tuple[None, None, None, str]:
    return None, None, None, input_buffer


def insert_text(input_buffer: str, cursor_pos: int, text: str) -> tuple[str, int]:
    cursor_pos = max(0, min(cursor_pos, len(input_buffer)))
    updated = input_buffer[:cursor_pos] + text + input_buffer[cursor_pos:]
    return updated, cursor_pos + len(text)


def delete_backspace(input_buffer: str, cursor_pos: int) -> tuple[str, int]:
    cursor_pos = max(0, min(cursor_pos, len(input_buffer)))
    if cursor_pos == 0:
        return input_buffer, cursor_pos
    updated = input_buffer[: cursor_pos - 1] + input_buffer[cursor_pos:]
    return updated, cursor_pos - 1


def delete_forward(input_buffer: str, cursor_pos: int) -> tuple[str, int]:
    cursor_pos = max(0, min(cursor_pos, len(input_buffer)))
    if cursor_pos >= len(input_buffer):
        return input_buffer, cursor_pos
    updated = input_buffer[:cursor_pos] + input_buffer[cursor_pos + 1 :]
    return updated, cursor_pos


def delete_prev_word(input_buffer: str, cursor_pos: int) -> tuple[str, int]:
    cursor_pos = max(0, min(cursor_pos, len(input_buffer)))
    if cursor_pos == 0:
        return input_buffer, cursor_pos

    left = input_buffer[:cursor_pos]
    right = input_buffer[cursor_pos:]
    i = len(left)

    while i > 0 and left[i - 1].isspace():
        i -= 1
    while i > 0 and not left[i - 1].isspace():
        i -= 1

    updated = left[:i] + right
    return updated, i


def clear_to_line_start(input_buffer: str, cursor_pos: int) -> tuple[str, int]:
    cursor_pos = max(0, min(cursor_pos, len(input_buffer)))
    updated = input_buffer[cursor_pos:]
    return updated, 0


def clear_to_line_end(input_buffer: str, cursor_pos: int) -> tuple[str, int]:
    cursor_pos = max(0, min(cursor_pos, len(input_buffer)))
    updated = input_buffer[:cursor_pos]
    return updated, cursor_pos


def _complete_token(
    original_buffer: str,
    body: str,
    token: str,
    candidates: list[str],
) -> str:
    if not candidates:
        return original_buffer
    matches = [item for item in candidates if item.startswith(token)]
    if not matches:
        return original_buffer

    replacement = token
    if len(matches) == 1:
        replacement = matches[0]
    else:
        shared = commonprefix(matches)
        if len(shared) > len(token):
            replacement = shared
        else:
            return original_buffer

    updated_body = body[: len(body) - len(token)] + replacement
    if len(matches) == 1:
        updated_body += " "
    return "\\" + updated_body


def _requires_approval(message: str) -> bool:
    return message.startswith(APPROVAL_REQUIRED_PREFIX)


def _inject_approve_flag(raw: str) -> str:
    if not raw.startswith("\\"):
        return raw
    if "--approve-risky" in raw:
        return raw
    return f"{raw} --approve-risky"


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
