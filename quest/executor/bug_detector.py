"""
Detects various types of bugs beyond what the LLM catches:
- App crashes (process died)
- App hangs (not responding)
- Memory leaks (RSS growing)
"""

import os
import subprocess
import glob as globmod
from datetime import datetime, timedelta


def check_crash(pid: int) -> dict | None:
    """
    Check if app crashed. Returns crash info dict or None.
    Looks at ~/Library/Logs/DiagnosticReports/ for recent crash logs.
    """
    # First check if process is alive
    try:
        os.kill(pid, 0)
        return None  # still running, no crash
    except OSError:
        pass  # process is gone

    # Look for recent crash reports
    crash_dir = os.path.expanduser("~/Library/Logs/DiagnosticReports")
    crash_info = {
        "pid": pid,
        "detected_at": datetime.now().isoformat(),
        "crash_log": None,
    }

    if os.path.isdir(crash_dir):
        cutoff = datetime.now() - timedelta(seconds=30)
        for path in sorted(globmod.glob(os.path.join(crash_dir, "*.ips")), reverse=True):
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(path))
                if mtime >= cutoff:
                    crash_info["crash_log"] = path
                    break
            except OSError:
                continue

    return crash_info


def check_hang(pid: int, timeout: float = 5.0) -> bool:
    """
    Check if app is hanging (not responding).
    Uses a simple AX query via the stub — if it takes too long, app is hung.
    """
    try:
        os.kill(pid, 0)
    except OSError:
        return False  # not hung, just dead

    # Try to query accessibility tree with a timeout
    try:
        from quest.scanner.ax_tree import get_ax_tree
        import threading

        result = [None]
        exc_holder = [None]

        def _query():
            try:
                result[0] = get_ax_tree(pid)
            except Exception as e:
                exc_holder[0] = e

        t = threading.Thread(target=_query, daemon=True)
        t.start()
        t.join(timeout=timeout)

        if t.is_alive():
            return True  # timed out — app is hung
        if exc_holder[0] is not None:
            return True  # AX query errored — likely hung

        return False
    except Exception:
        return False


def get_memory_usage(pid: int) -> int:
    """Get RSS memory in bytes for the process."""
    try:
        result = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(pid)],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip()) * 1024  # ps reports in KB
    except Exception:
        pass
    return 0


def detect_memory_leak(memory_readings: list[int],
                       threshold_growth_pct: float = 50.0) -> bool:
    """
    Given a list of memory readings over time, detect if there's a leak.
    If memory grew by more than threshold_growth_pct from first to last, flag it.
    """
    if len(memory_readings) < 2:
        return False
    first = max(memory_readings[0], 1)
    growth = (memory_readings[-1] - first) / first
    return growth > (threshold_growth_pct / 100)
