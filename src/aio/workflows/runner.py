from pathlib import Path


def run_workflow(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    return f"Executed workflow scaffold: {p.name}"
