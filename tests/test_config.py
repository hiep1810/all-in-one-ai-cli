from pathlib import Path

from aio.config.loader import load_config, update_config


def test_update_config_writes_value(tmp_path: Path):
    cfg_path = tmp_path / "config.yaml"
    update_config("model_provider", "llama_cpp", cfg_path)
    cfg = load_config(cfg_path)
    assert cfg.model_provider == "llama_cpp"


def test_update_config_parses_int(tmp_path: Path):
    cfg_path = tmp_path / "config.yaml"
    update_config("model_timeout_seconds", "12", cfg_path)
    cfg = load_config(cfg_path)
    assert cfg.model_timeout_seconds == 12


def test_update_config_sets_tui_theme(tmp_path: Path):
    cfg_path = tmp_path / "config.yaml"
    update_config("tui_theme", "matrix", cfg_path)
    cfg = load_config(cfg_path)
    assert cfg.tui_theme == "matrix"
