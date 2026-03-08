# Implementation Plan: Agent Loop v2 & Safety Sandbox

## 1. Goal Description

Based on the P0 Roadmap, we need to significantly upgrade the intelligence and safety of the CLI's core agent.
1.  **Agent Loop v2**: Replace the simplistic single-pass `AgentExecutor` with a robust, iterative ReAct (Reason + Act) loop. The AI must be able to plan, try a tool, observe its output (success or failure), and replan organically until the goal is achieved.
2.  **Safety Sandbox**: Before unleashing an iterative agent that can execute loops of tools autonomously, we must harden the `should_block_tool` logic. This includes introducing a strict filesystem sandbox and precise permission definitions for high-risk actions.

## 2. Approach

### A. Agent Loop v2 (ReAct)
1.  **The Context Window**: We will update `src/aio/agent/executor.py` so `run()` maintains an active `list[dict]` simulating a real conversational context between the system and the AI model.
2.  **The System Prompt**: We will inject a powerful system prompt instructing the model to output a strictly formatted JSON object on every turn containing its `"thought"`, the `"tool_name"`, and `"tool_kwargs"`.
3.  **The Loop**:
    *   Initialize `step = 0`. Set `MAX_STEPS = 10`.
    *   While `step < MAX_STEPS`:
        *   Ask the LLM for the next action.
        *   If the LLM returns `tool_name == "done"`, we break the loop and return the final answer.
        *   Otherwise, we execute the requested tool via `self.registry.run()`.
        *   We record the tool's raw string output (or python error traceback) and append it to the conversational context as a `user` or `tool` message: `{"role": "user", "content": "Tool Output: ..."}`.
        *   Increment `step`.

### B. Safety Sandbox
1.  **Allowed Path Sandbox**: Update `Config` to accept an `allowed_paths: list[str]` parameter. By default, it will only contain the current working directory `.`.
2.  **Tool Policy Levels**: Categorize tools in `src/aio/agent/policy.py`.
    *   `SAFE` (e.g. `fs.read`, `sys.env`): Auto-allowed in 'confirm' level. Always checked against `allowed_paths`.
    *   `RISKY` (e.g. `fs.write`, `shell.exec`, `mcp.*`): Blocked at 'strict' level, prompts TUI permission at 'confirm' level, auto-allowed at 'off' level.
3.  **Path Resolution Enforcement**: In `$AIO_HOME/src/aio/agent/safety.py`, we will write a `validate_path_sandbox(target_path, allowed_paths)` function that uses `Path.resolve()` to ensure no `../../../` relative path traversal escapes the designated sandbox bounds cleanly.

## 3. Implementation Steps

1.  **Sandbox Enforcements**
    *   Create `src/aio/agent/sandbox.py`. Implement `is_path_safe(requested_path: str | Path, cwd: Path) -> bool`.
    *   Update `src/aio/tools/filesystem.py` so `fs.read`, `fs.write`, `fs.search`, and `fs.list` immediately raise `ToolValidationError` if the `sandbox.is_path_safe` check fails.
2.  **Refactor Executor for Iteration (`src/aio/agent/executor.py`)**
    *   Rewrite `run()` to accept the initial `goal`.
    *   Create the `messages` array holding our ReAct system prompt and the user's goal.
    *   Implement the `while step < self.config.max_agent_steps: ...` loop.
    *   In the loop, pipe the LLM's response through a JSON parser.
    *   Wrap `registry.run()` in a `try/except Exception` block so the agent can receive detailed error strings and fix its own mistakes instead of crashing the CLI.
3.  **Refactor Safety/Approval hooks (`src/aio/tui/app.py`)**
    *   Because the tool loop is now highly recursive, the TUI must be capable of pausing the recursive thread if the agent picks a `shell.exec` or `fs.write` command in the middle of step 3, awaiting user input before the loop resumes.
    *   This will require updating how the TUI thread handles `queue` or async suspensions (Textual `@work` threading mechanisms).

## 4. Verification Plan

*   **Agent Loop Test**:
    1.  Ask the agent: `\agent create a file called test.txt with the word HELLO, then read it back to confirm.`
    2.  The TUI should show step 1 (writing), step 2 (reading), and then step 3 (reporting success).
*   **Sandbox Test**:
    1.  Ask the agent: `\agent read the contents of /etc/passwd or C:\Windows\System32\drivers\etc\hosts`.
    2.  The loop should instantly fail with a Sandbox Violation, and the LLM should see that failure and report it.

## 5. User Review Required

Does this dual-layered approach (modifying the `AgentExecutor` to be deeply recursive while simultaneously trapping all tools with `Path.resolve()` sandbox checks) cover what you intended for this phase?
