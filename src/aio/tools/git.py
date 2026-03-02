import subprocess
from pathlib import Path


def _run_git(command_args: list[str], cwd: str) -> str:
    path = Path(cwd)
    if not path.is_dir():
        raise NotADirectoryError(f"Directory not found: {cwd}")

    try:
        result = subprocess.run(
            ["git"] + command_args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Git error:\n{e.stderr.strip()}"
    except FileNotFoundError:
        return "Git executable not found. Is it installed and in your PATH?"


def git_status(path: str) -> str:
    """Returns the git status of the repository at the given path."""
    return _run_git(["status"], cwd=path)


def git_diff(path: str, staged: bool = False) -> str:
    """Returns the git diff for the given path. If staged is True, gets the diff of staged changes."""
    args = ["diff"]
    if staged:
        args.append("--staged")
    return _run_git(args, cwd=path)


def git_commit_draft(path: str, message: str) -> str:
    """Drafts a commit with the given message (only commits staged changes, does not push)."""
    return _run_git(["commit", "-m", message], cwd=path)


def git_branch_summary(path: str) -> str:
    """Returns a summary of branches in the repository."""
    return _run_git(["branch", "-a"], cwd=path)
