from __future__ import annotations

import argparse
import json
from pathlib import Path

from aio.agent.executor import AgentExecutor
from aio.agent.safety import should_block_tool
from aio.config.loader import config_to_dict, load_config, update_config, write_default_config
from aio.llm.router import get_client
from aio.logging.audit import AuditLogger
from aio.memory.session_store import SessionStore
from aio.tools.registry import ToolRegistry
from aio.utils.errors import ToolValidationError
from aio.workflows.runner import run_workflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aio", description="All-in-one AI CLI scaffold")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create local config/workspace")

    cfg = sub.add_parser("config", help="Show or update configuration")
    cfg_sub = cfg.add_subparsers(dest="cfg_cmd", required=True)
    cfg_sub.add_parser("show")
    cfg_set = cfg_sub.add_parser("set")
    cfg_set.add_argument("key")
    cfg_set.add_argument("value")

    ask = sub.add_parser("ask", help="One-shot prompt")
    ask.add_argument("prompt")
    ask.add_argument("--stream", action="store_true", help="Stream output when provider supports it")

    sub.add_parser("tui", help="Interactive terminal UI")

    chat = sub.add_parser("chat", help="Append message to session")
    chat.add_argument("message")
    chat.add_argument("--session", default="default")

    tool = sub.add_parser("tool", help="Run a tool")
    tool_sub = tool.add_subparsers(dest="tool_cmd", required=True)
    tool_run = tool_sub.add_parser("run")
    tool_run.add_argument("name")
    tool_run.add_argument("--arg", action="append", default=[], help="k=v")
    tool_run.add_argument("--approve-risky", action="store_true", help="Approve risky tools")

    agent = sub.add_parser("agent", help="Run agent")
    agent_sub = agent.add_subparsers(dest="agent_cmd", required=True)
    agent_run = agent_sub.add_parser("run")
    agent_run.add_argument("goal")
    agent_run.add_argument("--approve-risky", action="store_true", help="Approve risky tools")

    wf = sub.add_parser("workflow", help="Run workflow")
    wf_sub = wf.add_subparsers(dest="wf_cmd", required=True)
    wf_run = wf_sub.add_parser("run")
    wf_run.add_argument("path")

    replay = sub.add_parser("replay", help="Show a log file")
    replay.add_argument("run_id", help="Log filename under .aio/logs")

    return parser


def _parse_kv(items: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Invalid --arg value: {item}")
        k, v = item.split("=", 1)
        out[k] = v
    return out


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        cfg = write_default_config()
        print(f"Initialized at {cfg}")
        return 0

    if args.command == "config" and args.cfg_cmd == "set":
        cfg = update_config(args.key, args.value)
        print(f"Updated {args.key} in {cfg}")
        return 0

    config = load_config()
    logger = AuditLogger()

    if args.command == "config" and args.cfg_cmd == "show":
        print(json.dumps(config_to_dict(config), indent=2))
        return 0

    if args.command == "ask":
        client = get_client(config)
        if args.stream:
            chunks: list[str] = []
            for chunk in client.stream_complete(args.prompt):
                print(chunk, end="", flush=True)
                chunks.append(chunk)
            print()
            result = "".join(chunks)
        else:
            result = client.complete(args.prompt)
            print(result)
        logger.log({"cmd": "ask", "prompt": args.prompt, "stream": bool(args.stream)})
        return 0

    if args.command == "tui":
        from aio.tui.app import run_tui

        return run_tui()

    if args.command == "chat":
        store = SessionStore()
        path = store.append(args.session, {"role": "user", "content": args.message})
        print(f"Saved to {path}")
        logger.log({"cmd": "chat", "session": args.session})
        return 0

    if args.command == "tool" and args.tool_cmd == "run":
        registry = ToolRegistry()
        try:
            kwargs = _parse_kv(args.arg)
        except ValueError as exc:
            print(exc)
            return 1
        blocked, reason = should_block_tool(config.safety_level, args.name, args.approve_risky)
        if blocked:
            print(reason)
            return 1
        try:
            result = registry.run(args.name, **kwargs)
        except ToolValidationError as exc:
            print(exc)
            return 1
        print(result)
        logger.log({"cmd": "tool.run", "name": args.name})
        return 0

    if args.command == "agent" and args.agent_cmd == "run":
        registry = ToolRegistry()
        executor = AgentExecutor(config, registry)
        result = executor.run(args.goal, approve_risky=args.approve_risky)
        print(json.dumps(result, indent=2))
        logger.log({"cmd": "agent.run", "goal": args.goal})
        return 0

    if args.command == "workflow" and args.wf_cmd == "run":
        print(run_workflow(args.path))
        logger.log({"cmd": "workflow.run", "path": args.path})
        return 0

    if args.command == "replay":
        log_path = Path(".aio/logs") / args.run_id
        print(log_path.read_text(encoding="utf-8"))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
