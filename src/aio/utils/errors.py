class AIOError(Exception):
    """Base application error."""


class ConfigError(AIOError):
    """Raised when config is invalid or missing."""
