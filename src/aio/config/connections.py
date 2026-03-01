import json
from pathlib import Path

DEFAULT_CONNECTIONS_PATH = Path(".aio/connections.json")

DEFAULT_PRESETS = {
    "llama.cpp": {"url": "http://192.168.1.11:8080", "provider": "llama_cpp", "default_model": "local-model"},
    "lmstudio": {"url": "http://127.0.0.1:1234", "provider": "llama_cpp", "default_model": "local-model"},
    "ollama": {"url": "http://127.0.0.1:11434", "provider": "llama_cpp", "default_model": "llama3"}
}

def load_connection_presets() -> dict[str, dict[str, str]]:
    path = DEFAULT_CONNECTIONS_PATH
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(DEFAULT_PRESETS, indent=4), encoding="utf-8")
        return DEFAULT_PRESETS.copy()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_PRESETS.copy()
