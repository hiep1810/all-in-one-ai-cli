from collections.abc import Callable
from dataclasses import dataclass

from aio.tools import filesystem, shell
from aio.utils.errors import ToolValidationError

ToolFn = Callable[..., object]


@dataclass(frozen=True)
class ToolArgSpec:
    name: str
    expected_type: type
    required: bool = True


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolFn] = {
            "fs.read": filesystem.read_text,
            "fs.write": filesystem.write_text,
            "fs.search": filesystem.search_text,
            "shell.exec": shell.exec_cmd,
        }
        self._schemas: dict[str, list[ToolArgSpec]] = {
            "fs.read": [ToolArgSpec("path", str)],
            "fs.write": [ToolArgSpec("path", str), ToolArgSpec("content", str)],
            "fs.search": [ToolArgSpec("root", str), ToolArgSpec("query", str)],
            "shell.exec": [ToolArgSpec("cmd", str)],
        }

    def list_tools(self) -> list[str]:
        return sorted(self._tools.keys())

    def schema_for(self, name: str) -> list[ToolArgSpec]:
        if name not in self._schemas:
            raise ValueError(f"Unknown tool: {name}")
        return self._schemas[name]

    def _validate_kwargs(self, name: str, kwargs: dict[str, object]) -> None:
        schema = self.schema_for(name)
        allowed = {arg.name for arg in schema}
        required = {arg.name for arg in schema if arg.required}
        missing = sorted(key for key in required if key not in kwargs)
        if missing:
            raise ToolValidationError(
                f"Missing required args for {name}: {', '.join(missing)}"
            )

        unknown = sorted(key for key in kwargs if key not in allowed)
        if unknown:
            raise ToolValidationError(
                f"Unknown args for {name}: {', '.join(unknown)}"
            )

        for spec in schema:
            if spec.name not in kwargs:
                continue
            value = kwargs[spec.name]
            if not isinstance(value, spec.expected_type):
                expected = spec.expected_type.__name__
                got = type(value).__name__
                raise ToolValidationError(
                    f"Invalid type for {name}.{spec.name}: expected {expected}, got {got}"
                )

    def run(self, name: str, **kwargs: object) -> object:
        if name not in self._tools:
            raise ValueError(f"Unknown tool: {name}")
        self._validate_kwargs(name, kwargs)
        return self._tools[name](**kwargs)
