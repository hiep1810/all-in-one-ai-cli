from __future__ import annotations

from pathlib import Path

from aio.config.schema import Config


DEFAULT_CONFIG_PATH = Path(".aio/config.yaml")


def _parse_simple_yaml(text: str) -> dict[str, str]:
    """Minimal key: value parser to avoid extra deps in V1 scaffold."""
    data: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def load_config(path: Path | None = None) -> Config:
    cfg_path = path or DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        return Config()

    parsed = _parse_simple_yaml(cfg_path.read_text(encoding="utf-8"))
    return Config(
        model_provider=parsed.get("model_provider", "mock"),
        model_name=parsed.get("model_name", "mock-1"),
        model_base_url=parsed.get("model_base_url", "http://127.0.0.1:8080"),
        model_timeout_seconds=int(parsed.get("model_timeout_seconds", "60")),
        tui_theme=parsed.get("tui_theme", "neon"),
        safety_level=parsed.get("safety_level", "confirm"),
    )


def config_to_dict(config: Config) -> dict[str, str]:
    return {
        "model_provider": config.model_provider,
        "model_name": config.model_name,
        "model_base_url": config.model_base_url,
        "model_timeout_seconds": str(config.model_timeout_seconds),
        "tui_theme": config.tui_theme,
        "safety_level": config.safety_level,
    }


def save_config(config: Config, path: Path | None = None) -> Path:
    cfg_path = path or DEFAULT_CONFIG_PATH
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    data = config_to_dict(config)
    lines = [f"{key}: {value}" for key, value in data.items()]
    cfg_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return cfg_path


def update_config(key: str, value: str, path: Path | None = None) -> Path:
    config = load_config(path)
    if not hasattr(config, key):
        raise ValueError(f"Unknown config key: {key}")
    current = getattr(config, key)
    if isinstance(current, int):
        value = str(int(value))
        setattr(config, key, int(value))
    else:
        setattr(config, key, value)
    return save_config(config, path)


def write_default_config(path: Path | None = None) -> Path:
    cfg_path = path or DEFAULT_CONFIG_PATH
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    if not cfg_path.exists():
        cfg_path.write_text(
            """model_provider: mock
model_name: mock-1
model_base_url: http://127.0.0.1:8080
model_timeout_seconds: 60
tui_theme: neon
safety_level: confirm
""",
            encoding="utf-8",
        )
    return cfg_path
