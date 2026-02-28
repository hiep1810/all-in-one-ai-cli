import json
from pathlib import Path


class SessionStore:
    def __init__(self, root: Path = Path(".aio/sessions")):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def append(self, session: str, message: dict[str, str]) -> Path:
        path = self.root / f"{session}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(message, ensure_ascii=True) + "\n")
        return path
