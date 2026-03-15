"""
File system watcher for scan data.
Watches the scans/ directory for new files and emits log events
so the dashboard auto-updates when scans produce new data.
"""

import os
import time
import threading
import json
from quest.dashboard.logger import ghost_log
from quest import config


def watch_scans_dir(interval: float = 2.0):
    """
    Poll the scans directory for changes and emit log events.
    Runs in a background thread.
    """
    known_files = set()

    # Initial scan
    if os.path.isdir(config.SCANS_DIR):
        for root, dirs, files in os.walk(config.SCANS_DIR):
            for f in files:
                known_files.add(os.path.join(root, f))

    def _poll():
        nonlocal known_files
        while True:
            time.sleep(interval)
            if not os.path.isdir(config.SCANS_DIR):
                continue

            current_files = set()
            for root, dirs, files in os.walk(config.SCANS_DIR):
                for f in files:
                    current_files.add(os.path.join(root, f))

            new_files = current_files - known_files
            for fpath in sorted(new_files):
                relpath = os.path.relpath(fpath, config.SCANS_DIR)
                basename = os.path.basename(fpath)

                if basename == "app_graph.json":
                    ghost_log("system", "info", f"New app graph: {relpath}",
                              {"file": relpath})
                elif basename.startswith("test_cases"):
                    ghost_log("system", "info", f"New test cases: {relpath}",
                              {"file": relpath})
                elif basename.endswith((".png", ".jpg")):
                    ghost_log("system", "screenshot", f"New screenshot: {relpath}",
                              {"file": relpath}, screenshot=relpath)
                elif basename == "report.json":
                    ghost_log("system", "info", f"New report: {relpath}",
                              {"file": relpath})

            known_files = current_files

    thread = threading.Thread(target=_poll, daemon=True)
    thread.start()
    return thread
