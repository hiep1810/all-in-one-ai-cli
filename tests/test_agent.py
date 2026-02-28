from aio.agent.executor import AgentExecutor
from aio.config.schema import Config
from aio.tools.registry import ToolRegistry


def test_agent_run_returns_payload():
    result = AgentExecutor(Config(), ToolRegistry()).run("hello")
    assert result["goal"] == "hello"
