"""Quest CLI - AI-powered native macOS application tester."""

import json
import os
import sys
from datetime import datetime

from InquirerPy import inquirer
from InquirerPy.separator import Separator

from quest import app_manager, config
from quest.scanner.mapper import run_discovery
from quest.generator.test_generator import generate_tests
from quest.executor.agent_runner import run_agents
from quest.dashboard.logger import ghost_log
from quest.app_state import capture_snapshot, restore_snapshot, load_snapshot

BANNER = r"""
 ________                          __
\_____  \  __ __   ____   _______/  |_
 /  / \  \|  |  \_/ __ \ /  ___/\   __\
/   \_/.  \  |  /\  ___/ \___ \  |  |
\_____\ \_/____/  \___  >____  > |__|
       \__>           \/     \/
"""


def print_banner():
    print(BANNER)
    print("\u2500" * 40)


def load_personas() -> list[dict]:
    with open(config.PERSONAS_FILE) as f:
        return json.load(f)


def create_scan_dir(app_name: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scan_dir = os.path.join(config.SCANS_DIR, f"{app_name}_{timestamp}")
    os.makedirs(os.path.join(scan_dir, "screenshots"), exist_ok=True)
    os.makedirs(os.path.join(scan_dir, "reports"), exist_ok=True)
    return scan_dir


def save_app_graph(scan_dir: str, app_graph: dict):
    path = os.path.join(scan_dir, "app_graph.json")
    with open(path, "w") as f:
        json.dump(app_graph, f, indent=2)
    print(f"  Saved app graph to {path}")


def start_new_scan() -> tuple[dict, str] | None:
    """Run a new scan: select app, launch, discover, save."""
    apps = app_manager.list_applications()
    if not apps:
        print("No applications found in /Applications/")
        return None

    app_name = inquirer.fuzzy(
        message="Select an application to scan:",
        choices=apps,
        max_height="60%",
    ).execute()

    if not app_name:
        return None

    print(f"\n  Launching {app_name}...")
    try:
        pid = app_manager.launch_app(app_name)
    except RuntimeError as e:
        print(f"  Error: {e}")
        return None
    print(f"  {app_name} running (PID: {pid})")

    # --- Ask user to log in / set up the app first ---
    needs_login = inquirer.confirm(
        message="Does this app require login or setup before testing?",
        default=True,
    ).execute()

    if needs_login:
        print("\n  ┌─────────────────────────────────────────────┐")
        print("  │  Log into the app now and get it to the     │")
        print("  │  state you want testing to start from.      │")
        print("  │                                              │")
        print("  │  Press Enter when ready.                     │")
        print("  └─────────────────────────────────────────────┘\n")
        input("  Ready? Press Enter to continue...")

    scan_dir = create_scan_dir(app_name)

    # --- Capture app state snapshot (so we can restore between persona runs) ---
    if needs_login:
        print("  Capturing app state snapshot...")
        snapshot = capture_snapshot(app_name, scan_dir)
        print(f"  Snapshot saved ({len(snapshot['items'])} state items captured)")
        ghost_log("cli", "info", "App state snapshot captured",
                  {"items": list(snapshot["items"].keys())})

    print("  Running discovery scan...")
    app_graph = run_discovery(pid, app_name, scan_dir=scan_dir)
    print(f"  Found {app_graph['total_states']} states, {app_graph['total_elements']} elements")

    save_app_graph(scan_dir, app_graph)

    return app_graph, scan_dir


def load_existing_scan() -> tuple[dict, str] | None:
    """Load a previously saved scan."""
    if not os.path.isdir(config.SCANS_DIR):
        print("No scans directory found.")
        return None

    scan_folders = sorted(
        [d for d in os.listdir(config.SCANS_DIR)
         if os.path.isdir(os.path.join(config.SCANS_DIR, d))],
        reverse=True,
    )
    if not scan_folders:
        print("No existing scans found.")
        return None

    folder = inquirer.select(
        message="Select a scan to load:",
        choices=scan_folders,
    ).execute()

    scan_dir = os.path.join(config.SCANS_DIR, folder)
    graph_path = os.path.join(scan_dir, "app_graph.json")

    if not os.path.isfile(graph_path):
        print(f"  No app_graph.json found in {scan_dir}")
        return None

    with open(graph_path) as f:
        app_graph = json.load(f)

    print(f"  Loaded scan: {app_graph['app_name']} ({app_graph['total_states']} states, {app_graph['total_elements']} elements)")
    return app_graph, scan_dir


def select_personas(personas: list[dict]) -> list[dict]:
    """Prompt user to select personas with checkbox UI."""
    choices = [
        {"name": f"{p['name']} - {p['description']}", "value": p, "enabled": False}
        for p in personas
    ]

    selected = inquirer.checkbox(
        message="Select personas to run (space to toggle, enter to confirm):",
        choices=[
            {"name": "Select All", "value": "ALL"},
            Separator(),
            *choices,
        ],
        transformer=lambda result: f"{len(result)} selected",
    ).execute()

    if not selected:
        return []

    if "ALL" in selected:
        return personas

    return selected


def run_tests(app_graph: dict, scan_dir: str, personas: list[dict]):
    """Generate tests for each persona and execute them."""
    app_name = app_graph["app_name"]
    test_cases_by_persona = {}

    # Load snapshot if available (for restoring between persona runs)
    snapshot = load_snapshot(scan_dir)
    if snapshot:
        print(f"  Snapshot found — app state will be restored between persona runs\n")
    else:
        print(f"  No snapshot found — app state will NOT be reset between personas\n")

    print(f"  Generating tests for {len(personas)} persona(s)...\n")

    for persona in personas:
        print(f"  Generating tests for {persona['name']}...")
        tests = generate_tests(app_graph, persona, scan_dir)
        test_cases_by_persona[persona["id"]] = tests
        print(f"    Generated {len(tests)} test case(s)")

    total_tests = sum(len(tc) for tc in test_cases_by_persona.values())
    print(f"\n  Running {total_tests} test(s) across {len(personas)} persona(s)...\n")
    report = run_agents(app_name, test_cases_by_persona, app_graph, scan_dir,
                        snapshot=snapshot)

    print(f"\n{'=' * 40}")
    print(f"  RESULTS")
    print(f"{'=' * 40}")
    print(f"  Total tests: {report['total_tests']}")
    print(f"  Passed:      {report['passed']}")
    print(f"  Failed:      {report['failed']}")
    print(f"  Report:      {report['report_path']}")
    print(f"{'=' * 40}\n")


def main():
    print_banner()

    while True:
        action = inquirer.select(
            message="What would you like to do?",
            choices=[
                {"name": "[1] Start New Scan", "value": "new"},
                {"name": "[2] Load Existing Scan", "value": "load"},
                {"name": "[3] Open Dashboard", "value": "dashboard"},
                {"name": "[4] Exit", "value": "exit"},
            ],
        ).execute()

        if action == "exit":
            print("  Goodbye!")
            sys.exit(0)

        if action == "dashboard":
            from quest.dashboard.server import start_dashboard
            start_dashboard()
            continue

        if action == "new":
            result = start_new_scan()
        else:
            result = load_existing_scan()

        if result is None:
            continue

        app_graph, scan_dir = result

        personas = load_personas()
        selected = select_personas(personas)

        if not selected:
            print("  No personas selected. Returning to menu.\n")
            continue

        run_tests(app_graph, scan_dir, selected)


if __name__ == "__main__":
    main()
