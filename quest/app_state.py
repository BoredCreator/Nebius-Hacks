"""
App state snapshot and restore.

After the user logs into an app once, we capture:
  1. App preferences (~/Library/Preferences/<bundle_id>.plist)
  2. App container data (~/Library/Containers/<bundle_id>/)
  3. App support data (~/Library/Application Support/<app_name>/)
  4. App saved state (~/Library/Saved Application State/<bundle_id>.savedState/)
  5. Cookies (~/Library/Cookies/)

Before each persona run we restore this snapshot so the app
returns to the logged-in state without the user re-authenticating.
"""

import os
import shutil
import subprocess
import json
import plistlib
from pathlib import Path
from datetime import datetime

from quest.dashboard.logger import ghost_log


def get_bundle_id(app_name: str) -> str | None:
    """Get the bundle identifier for a .app by name."""
    app_path = f"/Applications/{app_name}.app"
    if not os.path.isdir(app_path):
        # Try case-insensitive search
        for entry in os.listdir("/Applications"):
            if entry.lower() == f"{app_name.lower()}.app":
                app_path = f"/Applications/{entry}"
                break

    info_plist = os.path.join(app_path, "Contents", "Info.plist")
    if not os.path.isfile(info_plist):
        return None

    try:
        with open(info_plist, "rb") as f:
            plist = plistlib.load(f)
        return plist.get("CFBundleIdentifier")
    except Exception:
        return None


def _find_state_paths(app_name: str, bundle_id: str | None) -> dict[str, str]:
    """Find all paths that store state for this app."""
    home = Path.home()
    paths = {}

    if bundle_id:
        # Preferences plist
        prefs = home / "Library" / "Preferences" / f"{bundle_id}.plist"
        if prefs.exists():
            paths["preferences"] = str(prefs)

        # Container (sandboxed apps)
        container = home / "Library" / "Containers" / bundle_id
        if container.exists():
            paths["container"] = str(container)

        # Saved application state
        saved = home / "Library" / "Saved Application State" / f"{bundle_id}.savedState"
        if saved.exists():
            paths["saved_state"] = str(saved)

        # HTTPStorages
        http_storage = home / "Library" / "HTTPStorages" / bundle_id
        if http_storage.exists():
            paths["http_storage"] = str(http_storage)

    # Application Support (by app name)
    app_support = home / "Library" / "Application Support" / app_name
    if app_support.exists():
        paths["app_support"] = str(app_support)

    # Also check with bundle ID for app support
    if bundle_id:
        app_support_bid = home / "Library" / "Application Support" / bundle_id
        if app_support_bid.exists():
            paths["app_support_bundle"] = str(app_support_bid)

    # Caches (some apps store auth tokens here)
    if bundle_id:
        caches = home / "Library" / "Caches" / bundle_id
        if caches.exists():
            paths["caches"] = str(caches)

    return paths


def capture_snapshot(app_name: str, scan_dir: str) -> dict:
    """
    Capture the current app state as a snapshot.
    Call this AFTER the user has logged in / set up the app.

    Returns a snapshot manifest dict that can be passed to restore_snapshot().
    """
    bundle_id = get_bundle_id(app_name)
    state_paths = _find_state_paths(app_name, bundle_id)

    snapshot_dir = os.path.join(scan_dir, "app_snapshot")
    os.makedirs(snapshot_dir, exist_ok=True)

    manifest = {
        "app_name": app_name,
        "bundle_id": bundle_id,
        "captured_at": datetime.now().isoformat(),
        "snapshot_dir": snapshot_dir,
        "items": {},
    }

    for label, src_path in state_paths.items():
        dest = os.path.join(snapshot_dir, label)
        try:
            if os.path.isdir(src_path):
                if os.path.exists(dest):
                    shutil.rmtree(dest)
                shutil.copytree(src_path, dest, symlinks=True)
            else:
                shutil.copy2(src_path, dest)

            manifest["items"][label] = {
                "source": src_path,
                "backup": dest,
                "is_dir": os.path.isdir(src_path),
            }
            ghost_log("system", "info", f"Snapshot: captured {label}",
                      {"source": src_path})
        except Exception as e:
            ghost_log("system", "warning", f"Snapshot: failed to capture {label}: {e}",
                      {"source": src_path})

    # Save manifest
    manifest_path = os.path.join(snapshot_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    ghost_log("system", "info",
              f"Snapshot captured: {len(manifest['items'])} items for {app_name}",
              {"bundle_id": bundle_id, "items": list(manifest["items"].keys())})

    return manifest


def restore_snapshot(manifest: dict, app_name: str) -> bool:
    """
    Restore app state from a snapshot.
    The app should be QUIT before calling this.

    1. Kill the app if running
    2. Restore all captured state files
    3. Re-launch the app

    Returns True on success.
    """
    from quest.app_manager import get_app_pid, kill_app, launch_app
    import time

    # Kill app if running
    pid = get_app_pid(app_name)
    if pid:
        kill_app(pid)
        time.sleep(1)

    items = manifest.get("items", {})
    restored = 0

    for label, info in items.items():
        src = info["backup"]       # our snapshot copy
        dest = info["source"]      # original location

        try:
            if info["is_dir"]:
                if os.path.exists(dest):
                    shutil.rmtree(dest)
                shutil.copytree(src, dest, symlinks=True)
            else:
                shutil.copy2(src, dest)
            restored += 1
        except Exception as e:
            ghost_log("system", "warning", f"Restore: failed {label}: {e}",
                      {"dest": dest})

    ghost_log("system", "info",
              f"Snapshot restored: {restored}/{len(items)} items for {app_name}")

    # Re-launch
    pid = launch_app(app_name)
    time.sleep(2)

    return restored == len(items)


def load_snapshot(scan_dir: str) -> dict | None:
    """Load a previously saved snapshot manifest from a scan directory."""
    manifest_path = os.path.join(scan_dir, "app_snapshot", "manifest.json")
    if not os.path.isfile(manifest_path):
        return None
    with open(manifest_path) as f:
        return json.load(f)
