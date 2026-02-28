RISKY_TOOLS = {"shell.exec", "fs.write"}


def is_risky_tool(tool_name: str) -> bool:
    return tool_name in RISKY_TOOLS


def should_block_tool(
    safety_level: str,
    tool_name: str,
    approve_risky: bool = False,
) -> tuple[bool, str]:
    if not is_risky_tool(tool_name):
        return False, ""

    if safety_level == "off":
        return False, ""
    if safety_level == "strict":
        return True, f"Blocked by strict safety policy: {tool_name}"
    if safety_level == "confirm" and not approve_risky:
        return True, (
            f"Approval required for risky tool: {tool_name}. "
            "Use --approve-risky (CLI) or --approve-risky in TUI command."
        )
    return False, ""
