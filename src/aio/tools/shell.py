import subprocess


def exec_cmd(cmd: str) -> str:
    proc = subprocess.run(cmd, shell=True, check=False, capture_output=True, text=True)
    out = proc.stdout.strip()
    err = proc.stderr.strip()
    if out and err:
        return f"stdout:\n{out}\n\nstderr:\n{err}"
    return out or err
