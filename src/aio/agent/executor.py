from aio.agent.planner import plan
from aio.agent.policy import is_allowed
from aio.agent.safety import should_block_tool
from aio.config.schema import Config
from aio.tools.registry import ToolRegistry


class AgentExecutor:
    def __init__(self, config: Config, registry: ToolRegistry):
        self.config = config
        self.registry = registry

    def run(self, goal: str, approve_risky: bool = False) -> dict[str, object]:
        steps = plan(goal)
        # Demonstrate a single safe tool action.
        action = "shell.exec"
        tool_result = "skipped by policy"
        blocked, reason = should_block_tool(self.config.safety_level, action, approve_risky)
        if blocked:
            tool_result = reason
            return {"goal": goal, "steps": steps, "tool": action, "result": tool_result}
        if is_allowed(self.config.safety_level, action):
            tool_result = self.registry.run(action, cmd=f"echo {goal!r}")
        return {"goal": goal, "steps": steps, "tool": action, "result": tool_result}
