"""
Centralized structured logging for Quest.
All phases import this module to emit events.

Events are:
1. Written to logs/appghost.log (JSON lines format)
2. Broadcast via WebSocket to the dashboard for real-time display
3. Stored in an in-memory ring buffer for the dashboard API

Usage:
    from quest.dashboard.logger import ghost_log

    ghost_log("mapper", "info", "Starting DFS exploration",
              {"pid": 12345, "app": "Calculator"})
"""

import json
import os
import time
from datetime import datetime
from collections import deque
from typing import Any

# In-memory storage
LOG_BUFFER = deque(maxlen=10000)
EVENT_LISTENERS = []  # WebSocket connections to notify

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "appghost.log")

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)


def ghost_log(source: str, level: str, message: str,
              data: dict = None, screenshot: str = None) -> dict:
    """
    Emit a structured log event.

    Args:
        source: Which phase emitted this. One of:
                "cli", "mapper", "ax_tree", "interactions", "vision",
                "generator", "executor", "bug_detector", "reporter", "system"
        level: Event type/severity. One of:
               "debug", "info", "warning", "error", "critical",
               "action", "state_change", "llm_call", "llm_response",
               "test_start", "test_step", "test_end",
               "bug", "screenshot", "phase_start", "phase_end"
        message: Human-readable description
        data: Arbitrary dict of structured data
        screenshot: Path to a screenshot file if relevant

    Returns:
        The log event dict (for chaining/testing)
    """
    event = {
        "id": f"{source}_{int(time.time() * 1000)}_{len(LOG_BUFFER)}",
        "timestamp": datetime.now().isoformat(),
        "epoch_ms": int(time.time() * 1000),
        "source": source,
        "level": level,
        "message": message,
        "data": data or {},
        "screenshot": screenshot,
    }

    # Add to in-memory buffer
    LOG_BUFFER.append(event)

    # Write to log file (JSON lines)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(event) + "\n")
    except OSError:
        pass

    # Notify WebSocket listeners (non-blocking)
    _notify_listeners(event)

    # Also print to console with color
    _console_print(event)

    return event


def _console_print(event: dict):
    """Pretty print to terminal with colors."""
    colors = {
        "debug": "\033[90m",
        "info": "\033[36m",
        "warning": "\033[33m",
        "error": "\033[31m",
        "critical": "\033[41m",
        "action": "\033[35m",
        "state_change": "\033[32m",
        "llm_call": "\033[34m",
        "llm_response": "\033[34m",
        "test_start": "\033[96m",
        "test_step": "\033[36m",
        "test_end": "\033[96m",
        "bug": "\033[91m",
        "screenshot": "\033[90m",
        "phase_start": "\033[92m",
        "phase_end": "\033[92m",
    }
    reset = "\033[0m"
    color = colors.get(event["level"], "\033[0m")
    ts = event["timestamp"].split("T")[1][:12]
    src = event["source"].ljust(12)
    lvl = event["level"].ljust(14)
    print(f"{color}[{ts}] [{src}] [{lvl}] {event['message']}{reset}")
    if event["data"]:
        for k, v in event["data"].items():
            val_str = str(v)[:100]
            print(f"{color}  \u2514\u2500 {k}: {val_str}{reset}")


def _notify_listeners(event: dict):
    """Send event to all connected WebSocket clients."""
    for listener in EVENT_LISTENERS:
        try:
            listener(event)
        except Exception:
            pass


def get_recent_logs(n: int = 100, source: str = None,
                    level: str = None) -> list[dict]:
    """Get recent log events with optional filtering.
    Falls back to reading the log file if the in-memory buffer is empty
    (happens when scanner runs in a separate process).
    """
    logs = list(LOG_BUFFER)

    # If buffer is empty/small, hydrate from log file
    if len(logs) < 5 and os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            logs.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except OSError:
            pass

    if source:
        logs = [l for l in logs if l["source"] == source]
    if level:
        logs = [l for l in logs if l["level"] == level]
    return logs[-n:]


def get_stats() -> dict:
    """Get aggregate stats from the log buffer."""
    logs = list(LOG_BUFFER)
    return {
        "total_events": len(logs),
        "by_source": _count_by(logs, "source"),
        "by_level": _count_by(logs, "level"),
        "bugs_found": len([l for l in logs if l["level"] == "bug"]),
        "llm_calls": len([l for l in logs if l["level"] == "llm_call"]),
        "screenshots_taken": len([l for l in logs if l["level"] == "screenshot"]),
        "errors": len([l for l in logs if l["level"] in ("error", "critical")]),
        "first_event": logs[0]["timestamp"] if logs else None,
        "last_event": logs[-1]["timestamp"] if logs else None,
    }


def _count_by(logs, key):
    counts = {}
    for l in logs:
        val = l[key]
        counts[val] = counts.get(val, 0) + 1
    return counts
