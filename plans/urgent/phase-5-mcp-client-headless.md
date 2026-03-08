# Phase 5 — MCP Client + Headless Output + Per-Tool Permissions

## What This Phase Does (Big Picture)

aio can already **serve** tools via MCP (other AI clients can use aio's tools). But it can't **consume** external MCP servers. This phase closes that gap — plus two bonus features:

1. **MCP Client** — connect to external MCP servers (GitHub, Slack, databases, etc.)  
2. **Headless JSON output** — `aio ask "query" --output-format json` for scripting/CI
3. **Per-tool permissions** — fine-grained control over which tools are allowed

> **Junior tip:** MCP is like USB for AI tools. Any tool (server) that speaks MCP can be plugged into any AI (client) that speaks MCP. Right now aio is a USB device but not a USB hub — this phase makes it a hub too.

## Inspired By

| Tool | How They Do It |
|:--|:--|
| **Claude Code** | `--mcp-config ./mcp.json`, full stdio + SSE client |
| **Gemini CLI** | `@server` prefix to route prompts to MCP tools |
| **OpenCode** | MCP client with stdio + SSE, auto-discovery of tools |

## Design Patterns Used

### 1. Client-Server (JSON-RPC 2.0)

- **One-Line ELI5:** Two programs talk to each other by sending structured JSON messages — one asks questions (client), the other answers (server).
- **Why Here:** MCP uses JSON-RPC 2.0 as its wire protocol. Our existing MCP *server* already implements it. Now we build the other side — the *client* that sends requests and reads responses.
- **Real Analogy:** Like a drive-through — you (client) speak into the microphone (send request), the restaurant (server) prepares your food (processes request), and hands it through the window (sends response).

### 2. Process Manager (for MCP server lifecycle)

- **One-Line ELI5:** A component that starts, monitors, and stops child processes.
- **Why Here:** Each MCP server runs as a separate process (started via `subprocess.Popen`). The manager starts them all on init, tracks their health, and kills them on exit.
- **Real Analogy:** Like a daycare manager — they check each kid (process) in, monitor them during the day, and make sure everyone goes home at closing time.

### 3. Strategy Pattern (for output formats)

- **One-Line ELI5:** Different behaviors selected at runtime based on a parameter.
- **Why Here:** `--output-format text` prints plain text, `--output-format json` prints JSON, `--output-format stream-json` prints streaming events. Same data, different formatting strategy.
- **Real Analogy:** Like export options in a spreadsheet — you have the same data, but you can export it as CSV, PDF, or Excel depending on what you need.

### 4. Access Control List (ACL) — for permissions

- **One-Line ELI5:** A list that says who (which tool) is allowed to do what (allow/deny/ask).
- **Why Here:** Instead of three coarse levels (off/confirm/strict), each tool gets its own permission. `fs.read: allow`, `shell.exec: ask`, `web.fetch: deny`. More control without more complexity.
- **Real Analogy:** Like app permissions on your phone — Camera: allowed, Microphone: ask every time, Location: denied.

## Files to Create/Modify

```
src/aio/
├── mcp/
│   ├── server.py          (existing, untouched)
│   ├── client.py          ← NEW (MCP client connection)
│   └── manager.py         ← NEW (multi-server lifecycle)
├── tools/
│   └── registry.py        ← MODIFY (merge MCP tools into registry)
├── agent/
│   └── safety.py          ← MODIFY (per-tool permissions)
├── config/
│   └── schema.py          ← MODIFY (add tool_permissions field)
├── tui/
│   └── app.py             ← MODIFY (\mcp commands)
└── cli.py                 ← MODIFY (--output-format flag)
```

---

## Detailed Implementation

### [NEW] `src/aio/mcp/client.py`

```python
class MCPClient:
    """
    Connects to a single MCP server via stdio (subprocess).
    
    Lifecycle:
    1. __init__(command, args, env) — stores config
    2. connect() — spawns process, sends 'initialize', waits for response
    3. list_tools() — sends 'tools/list', returns tool definitions
    4. call_tool(name, args) — sends 'tools/call', returns result
    5. close() — sends EOF, terminates process
    
    Why stdio (not HTTP/SSE):
    - Simpler — no web server needed
    - More portable — works everywhere Python's subprocess works
    - Same transport used by Claude Code and Gemini CLI by default
    - SSE support can be added later as a second transport
    
    Wire format (same as our existing server):
    - Content-Length header + \r\n\r\n + JSON body
    - Each message is a JSON-RPC 2.0 request or response
    """
    
    def __init__(self, command: str, args: list[str], env: dict = None):
        self.command = command
        self.args = args
        self.env = env or {}
        self._process = None
        self._request_id = 0
    
    def connect(self) -> dict:
        """Spawns the subprocess and sends initialize."""
    
    def list_tools(self) -> list[dict]:
        """Returns tool definitions from the server."""
    
    def call_tool(self, name: str, arguments: dict) -> dict:
        """Calls a tool and returns the result content."""
    
    def close(self):
        """Terminates the subprocess."""
```

> **Junior tip:** `subprocess.Popen` starts a new program and gives you pipes to its stdin/stdout. We write JSON requests to stdin and read JSON responses from stdout. It's like having a text conversation with another program.

### [NEW] `src/aio/mcp/manager.py`

```python
class MCPManager:
    """
    Manages multiple MCP server connections.
    
    Reads config from .aio/mcp.json (same format as mcp.example.json):
    {
        "servers": {
            "github": {"command": "npx", "args": ["@github/mcp-server"]},
            "web": {"command": "uvx", "args": ["kindly-web-search-mcp-server"]}
        }
    }
    """
    
    def __init__(self, config_path: Path = Path(".aio/mcp.json")):
        self.config_path = config_path
        self._clients: dict[str, MCPClient] = {}
    
    def start_all(self):
        """Starts all configured servers and calls connect()."""
    
    def get_all_tools(self) -> dict[str, list[dict]]:
        """
        Returns tools from all servers, keyed by server name.
        {"github": [{"name": "list_prs", ...}], "web": [{"name": "search", ...}]}
        """
    
    def call(self, server: str, tool: str, arguments: dict) -> dict:
        """Calls a tool on a specific server."""
    
    def stop_all(self):
        """Closes all connections and terminates all processes."""
```

### [MODIFY] `src/aio/tools/registry.py`

**After loading built-in tools**, also load MCP tools:

```python
def __init__(self, mcp_manager: MCPManager | None = None):
    # ... existing built-in tools ...
    
    # Load MCP tools if available
    if mcp_manager:
        for server_name, tools in mcp_manager.get_all_tools().items():
            for tool in tools:
                full_name = f"{server_name}.{tool['name']}"
                self._tools[full_name] = lambda **kw, s=server_name, t=tool['name']: (
                    mcp_manager.call(s, t, kw)
                )
                # Convert MCP inputSchema to ToolArgSpec
```

> **Junior tip:** The tricky `lambda **kw, s=server_name, t=tool['name']:` uses default arguments to capture the current loop values. Without `s=server_name`, all lambdas would reference the *last* value of `server_name` (a common Python gotcha called "closure over loop variable").

### [MODIFY] `src/aio/agent/safety.py`

Replace `RISKY_TOOLS` set with configurable permissions:

```python
def should_block_tool(
    safety_level: str,
    tool_name: str,
    approve_risky: bool = False,
    tool_permissions: dict[str, str] | None = None,
) -> tuple[bool, str]:
    """
    New behavior:
    1. Check tool_permissions first (if provided)
       - "allow" → never block
       - "deny" → always block
       - "ask" → block unless approve_risky=True
    2. Support glob patterns: "shell.*" matches "shell.exec"
    3. Fall back to safety_level if no specific permission
    
    Uses fnmatch for glob matching — same as file path matching.
    """
```

### [MODIFY] `src/aio/cli.py`

Add `--output-format` to `aio ask`:

```python
ask.add_argument("--output-format", choices=["text", "json"], default="text")

# In the ask handler:
if args.output_format == "json":
    print(json.dumps({"result": result, "model": config.model_name}))
else:
    print(result)
```

---

## Tests

### [NEW] `tests/test_mcp_client.py`

```python
def test_mcp_client_connect(mock_subprocess):
    # Mock Popen, verify initialize sent and response parsed

def test_mcp_client_list_tools(mock_subprocess):
    # Mock tools/list response → verify returned list

def test_mcp_client_call_tool(mock_subprocess):
    # Mock tools/call response → verify result content

def test_mcp_manager_discovers_tools(tmp_path):
    # Create mcp.json with mock server → verify get_all_tools works
```

### [MODIFY] `tests/test_cli.py`

```python
def test_ask_json_output(mock_get_client):
    # aio ask "hello" --output-format json → valid JSON with "result" key
```

### [MODIFY] `tests/test_safety.py`

```python
def test_tool_permissions_allow():
    # fs.read with permission "allow" → not blocked even in strict mode

def test_tool_permissions_deny():
    # web.fetch with permission "deny" → blocked even in off mode

def test_tool_permissions_glob():
    # "shell.*: ask" → shell.exec requires approval
```

## How to Verify Manually

1. Add to `.aio/mcp.json`: `{"servers": {"aio": {"command": "aio-mcp", "args": ["--root", "."]}}}` → `aio tui` → `\mcp list` → see aio's own tools
2. Run `aio ask "hello" --output-format json` → valid JSON output
3. Add `tool_permissions: {shell.*: deny}` to config → `\tool shell.exec cmd='echo hi'` → blocked
