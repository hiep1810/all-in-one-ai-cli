# Implementation Plan: Strict Tool Contracts 

## 1. Goal Description

Before allowing an autonomous ReAct agent loop to execute logic rapidly, our tool layer must be perfectly hardened. `src/aio/tools/registry.py` currently uses a very basic dataclass `ToolArgSpec` that only checks surface-level types (`str`, `int`). 
We need to upgrade the "Tool Contract" so that every tool defines:
1.  **Detailed JSON Schema**: For the LLM to understand what the tool does and what arguments it accepts.
2.  **Runtime Timeouts**: So a frozen shell command doesn't permanently hang the CLI.
3.  **Strict Validation**: If the LLM hallucinates an argument, the tool registry catches it instantly and returns a standardized `ToolValidationError` string to the LLM so it can retry gracefully.

## 2. Approach

1.  **Schema Generation**: We will migrate away from the manual `ToolArgSpec` tuples in `registry.py` and strictly type every tool function's signature. We can use Python's built-in `inspect` and `typing` modules (or `pydantic` if we add it to the project) to dynamically generate the JSON schema for the LLM.
2.  **Timeout Wrappers**: We will add a `timeout_seconds` configuration to the tool registry. When `self.registry.run(tool_name)` is called, it will execute the underlying function via a thread or `asyncio.wait_for` to ensure it aborts forcefully if it exceeds the limit (e.g., 30 seconds).
3.  **Standardized Response Format**: Right now, tools return plain strings, booleans, or nothing. We will wrap all tool returns in a consistent schema: `{"status": "success|error", "output": "..." }` so the Iterative loop always knows exactly how to parse the result.

## 3. Implementation Steps

1.  **Update `ToolRegistry` Validation (`src/aio/tools/registry.py`)**
    *   Currently, `_schemas` is hardcoded. We will write a helper `_generate_schema(fn)` that reads the docstring and type hints of functions like `filesystem.read_text` to automatically construct the JSON schema dictionary that OpenAI/Anthropic APIs expect.
    *   Change `list_tools()` or add `get_tool_schemas()` to return the full list of these JSON schema dicts.
2.  **Add Execution Timeouts**
    *   In `registry.run()`, wrap the `self._tools[name](**kwargs)` call in a `concurrent.futures.ThreadPoolExecutor` submission, and use `future.result(timeout=30)`.
    *   Catch `TimeoutError` and return it as a structured tool failure: `{"status": "error", "output": "Tool execution timed out after 30 seconds."}`.
3.  **Standardize Return Results**
    *   Modify all functions in `src/aio/tools/filesystem.py`, `shell.py`, etc., to return stringified results strictly.
    *   Inside `registry.run()`, trap *all* custom exceptions (like `ToolValidationError` or `PermissionError`) and return them as `{"status": "error", "output": str(exc)}`. If it succeeds, return `{"status": "success", "output": str(result)}`.

## 4. Verification Plan

*   **Timeout Test**:
    1.  Create a dummy tool `sleep_tool` that `time.sleep(40)`.
    2.  Execute it via the TUI `\tool sleep_tool`.
    3.  Verify the CLI doesn't hang forever, but returns the timeout error string after exactly 30 seconds.
*   **Validation Test**:
    1.  Execute `\tool fs.read unexpected_arg=True`.
    2.  Verify it rejects the payload and immediately returns `{"status": "error", "output": "Unknown args... expected 'path'"}` rather than crashing the python process.

## 5. User Review Required

Does this architecture for generating schemas, enforcing timeouts, and safely wrapping outputs match your vision for finishing the **P0 Tool Contracts** milestone?
