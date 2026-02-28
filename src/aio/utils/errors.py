class AIOError(Exception):
    """Base application error."""


class ConfigError(AIOError):
    """Raised when config is invalid or missing."""


class ToolValidationError(AIOError):
    """Raised when tool arguments are invalid."""
