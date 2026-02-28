import json
from datetime import datetime, timezone
from pathlib import Path


class AuditLogger:
    def __init__(self, root: Path = Path(".aio/logs")):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def log(self, event: dict[str, object]) -> Path:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = self.root / f"{day}.jsonl"
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            **event,
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")
        return path
