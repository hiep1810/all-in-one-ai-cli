from pathlib import Path
from typing import List


def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_text(path: str, content: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return str(p)


def search_text(root: str, query: str) -> List[str]:
    root_path = Path(root)
    matches: list[str] = []
    for p in root_path.rglob("*"):
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if query in text:
            matches.append(str(p))
    return matches
