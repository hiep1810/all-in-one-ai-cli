from aio.agent.safety import is_risky_tool, should_block_tool


def test_is_risky_tool():
    assert is_risky_tool("shell.exec")
    assert is_risky_tool("fs.write")
    assert not is_risky_tool("fs.search")


def test_confirm_requires_approval_for_risky_tool():
    blocked, reason = should_block_tool("confirm", "shell.exec", approve_risky=False)
    assert blocked
    assert "Approval required" in reason


def test_confirm_allows_when_approved():
    blocked, _ = should_block_tool("confirm", "shell.exec", approve_risky=True)
    assert not blocked


def test_strict_blocks_risky_tool():
    blocked, reason = should_block_tool("strict", "fs.write", approve_risky=True)
    assert blocked
    assert "Blocked by strict safety policy" in reason
