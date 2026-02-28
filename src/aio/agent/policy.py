def is_allowed(safety_level: str, tool_name: str) -> bool:
    if safety_level == "off":
        return True
    if safety_level == "strict" and tool_name.startswith("shell"):
        return False
    return True
