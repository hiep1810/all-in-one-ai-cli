from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SERVER_NAME = "aio-mcp"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2024-11-05"


def _read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        decoded = line.decode("utf-8").strip()
        if ":" not in decoded:
            continue
        key, value = decoded.split(":", 1)
        headers[key.strip().lower()] = value.strip()

    length_raw = headers.get("content-length")
    if length_raw is None:
        return None
    length = int(length_raw)
    body = sys.stdin.buffer.read(length)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def _write_message(payload: dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(data)}\r\n\r\n".encode("utf-8"))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def _make_response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _make_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _resolve_path(root: Path, raw_path: str) -> Path:
    candidate = (root / raw_path).resolve() if not Path(raw_path).is_absolute() else Path(raw_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path outside allowed root: {raw_path}") from exc
    return candidate


def _tool_list() -> list[dict[str, Any]]:
    return [
        {
            "name": "read_file",
            "description": "Read a UTF-8 text file from project root.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "max_chars": {"type": "integer", "default": 20000},
                },
                "required": ["path"],
            },
        },
        {
            "name": "read_markdown",
            "description": "Read a markdown (.md) file from project root.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "max_chars": {"type": "integer", "default": 20000},
                },
                "required": ["path"],
            },
        },
        {
            "name": "list_files",
            "description": "List files under a directory (relative to project root).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "root": {"type": "string", "default": "."},
                    "glob": {"type": "string", "default": "**/*"},
                    "limit": {"type": "integer", "default": 200},
                },
            },
        },
    ]


def _text_result(text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}]}


def _handle_tool_call(root: Path, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "read_file":
        raw_path = str(arguments.get("path", "")).strip()
        if not raw_path:
            raise ValueError("Missing required argument: path")
        max_chars = int(arguments.get("max_chars", 20000))
        path = _resolve_path(root, raw_path)
        text = path.read_text(encoding="utf-8")
        return _text_result(text[:max_chars])

    if name == "read_markdown":
        raw_path = str(arguments.get("path", "")).strip()
        if not raw_path:
            raise ValueError("Missing required argument: path")
        if not raw_path.lower().endswith(".md"):
            raise ValueError("Path must end with .md")
        max_chars = int(arguments.get("max_chars", 20000))
        path = _resolve_path(root, raw_path)
        text = path.read_text(encoding="utf-8")
        return _text_result(text[:max_chars])

    if name == "list_files":
        raw_root = str(arguments.get("root", "."))
        pattern = str(arguments.get("glob", "**/*"))
        limit = max(1, min(int(arguments.get("limit", 200)), 1000))
        base = _resolve_path(root, raw_root)
        items: list[str] = []
        for p in base.glob(pattern):
            if not p.is_file():
                continue
            items.append(str(p.relative_to(root)))
            if len(items) >= limit:
                break
        return _text_result("\n".join(items))

    raise ValueError(f"Unknown tool: {name}")


def _handle_request(root: Path, req: dict[str, Any]) -> dict[str, Any] | None:
    method = req.get("method")
    request_id = req.get("id")

    if method == "initialize":
        return _make_response(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return _make_response(request_id, {"tools": _tool_list()})

    if method == "tools/call":
        params = req.get("params", {})
        name = str(params.get("name", ""))
        args = params.get("arguments", {})
        if not isinstance(args, dict):
            args = {}
        try:
            result = _handle_tool_call(root, name, args)
            return _make_response(request_id, result)
        except Exception as exc:
            return _make_error(request_id, -32000, str(exc))

    if request_id is None:
        return None
    return _make_error(request_id, -32601, f"Method not found: {method}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aio-mcp", description="MCP server for all-in-one-ai-cli")
    parser.add_argument("--root", default=".", help="Allowed project root for file access")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        print(f"Invalid --root path: {root}", file=sys.stderr)
        return 1

    while True:
        req = _read_message()
        if req is None:
            return 0
        resp = _handle_request(root, req)
        if resp is not None:
            _write_message(resp)


if __name__ == "__main__":
    raise SystemExit(main())
