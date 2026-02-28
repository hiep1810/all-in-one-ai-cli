from dataclasses import dataclass


@dataclass
class Config:
    model_provider: str = "mock"
    model_name: str = "mock-1"
    model_base_url: str = "http://127.0.0.1:8080"
    model_timeout_seconds: int = 60
    tui_theme: str = "neon"  # neon | minimal | matrix
    safety_level: str = "confirm"  # off | confirm | strict
