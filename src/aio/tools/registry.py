from collections.abc import Callable

from aio.tools import filesystem, shell

ToolFn = Callable[..., object]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolFn] = {
            "fs.read": filesystem.read_text,
            "fs.write": filesystem.write_text,
            "fs.search": filesystem.search_text,
            "shell.exec": shell.exec_cmd,
        }

    def list_tools(self) -> list[str]:
        return sorted(self._tools.keys())

    def run(self, name: str, **kwargs: object) -> object:
        if name not in self._tools:
            raise ValueError(f"Unknown tool: {name}")
        return self._tools[name](**kwargs)
