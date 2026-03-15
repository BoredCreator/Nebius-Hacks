"""Application management: list, launch, get PID, and kill macOS apps."""

import os
import subprocess
import time
from quest.dashboard.logger import ghost_log

from quest.config import APPLICATIONS_DIR


def list_applications() -> list[str]:
    """List all .app bundles in /Applications/."""
    apps = []
    for entry in sorted(os.listdir(APPLICATIONS_DIR)):
        if entry.endswith(".app"):
            apps.append(entry.removesuffix(".app"))
    return apps


def launch_app(app_name: str) -> int:
    """Launch a macOS app by name and return its PID after waiting for it to start."""
    subprocess.Popen(["open", "-a", app_name])
    time.sleep(3)
    pid = get_app_pid(app_name)
    if pid is None:
        raise RuntimeError(f"Failed to get PID for '{app_name}' after launch")
    return pid


def get_app_pid(app_name: str) -> int | None:
    """Get the PID of a running app by name using pgrep."""
    try:
        result = subprocess.run(
            ["pgrep", "-x", app_name],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip().splitlines()[0])
    except Exception:
        pass
    return None


def kill_app(pid: int) -> None:
    """Kill an app by PID."""
    try:
        subprocess.run(["kill", str(pid)], check=True)
    except subprocess.CalledProcessError:
        subprocess.run(["kill", "-9", str(pid)], check=False)
