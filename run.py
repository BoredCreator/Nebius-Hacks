#!/usr/bin/env python3
"""
Quest - Single entry point.
Usage:
    python run.py                    # Normal mode: CLI + dashboard
    python run.py --verify           # Run verification suite
    python run.py --dashboard-only   # Just start the dashboard
    python run.py --demo             # Demo mode: run against Calculator with all personas
    python run.py --quick-test       # Quick smoke test against TextEdit
"""

import sys
import os
import argparse
import threading
import time
import json

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quest.config import validate_environment, DASHBOARD_PORT, PERSONAS_FILE
from quest.dashboard.logger import ghost_log


def main():
    parser = argparse.ArgumentParser(description="Quest - AI App Tester")
    parser.add_argument("--verify", action="store_true", help="Run verification suite")
    parser.add_argument("--dashboard-only", action="store_true", help="Only start dashboard")
    parser.add_argument("--demo", action="store_true", help="Demo mode against Calculator")
    parser.add_argument("--quick-test", action="store_true", help="Quick smoke test")
    parser.add_argument("--no-dashboard", action="store_true", help="Skip dashboard")
    parser.add_argument("--app", type=str, help="App name to test directly")
    parser.add_argument("--personas", type=str, nargs="+", help="Persona IDs to use")
    args = parser.parse_args()

    # === VERIFY MODE ===
    if args.verify:
        from verify import run_all_verifications
        run_all_verifications()
        return

    # === ENVIRONMENT CHECK ===
    ghost_log("system", "info", "Quest starting up")
    checks = validate_environment()
    all_passed = True
    for name, (passed, msg) in checks.items():
        status = "+" if passed else "x"
        print(f"  [{status}] {msg}")
        if not passed:
            all_passed = False
            ghost_log("system", "warning", f"Environment check failed: {name}", {"message": msg})

    if not all_passed:
        print("\n  Some checks failed. Continuing anyway, but things may break.\n")

    # === START DASHBOARD ===
    if not args.no_dashboard:
        start_dashboard_background()
        time.sleep(1)
        print(f"  Dashboard: http://localhost:{DASHBOARD_PORT}\n")

    # === DASHBOARD ONLY MODE ===
    if args.dashboard_only:
        print("Dashboard running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down.")
        return

    # === DEMO MODE ===
    if args.demo:
        run_demo_mode()
        return

    # === QUICK TEST MODE ===
    if args.quick_test:
        run_quick_test()
        return

    # === DIRECT APP MODE ===
    if args.app:
        run_direct(args.app, args.personas)
        return

    # === NORMAL CLI MODE ===
    from quest.cli import main as cli_main
    cli_main()


def start_dashboard_background():
    """Start the dashboard server in a background thread."""
    def _run():
        import uvicorn
        from quest.dashboard.server import app
        uvicorn.run(app, host="0.0.0.0", port=DASHBOARD_PORT, log_level="warning")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    ghost_log("system", "info", f"Dashboard started on port {DASHBOARD_PORT}")


def run_demo_mode():
    """Run a complete demo against Calculator."""
    ghost_log("system", "info", "DEMO MODE: Running full pipeline against Calculator")

    from quest.app_manager import launch_app, get_app_pid, kill_app
    from quest.scanner.mapper import run_discovery
    from quest.generator.test_generator import generate_tests
    from quest.executor.agent_runner import run_agents
    from quest.executor.report_generator import generate_report, generate_markdown_report
    from quest.config import get_scan_dir

    app_name = "Calculator"
    scan_dir = str(get_scan_dir(app_name))

    print(f"\n  Quest Demo Mode")
    print(f"   App: {app_name}")
    print(f"   Scan dir: {scan_dir}")
    print(f"   Dashboard: http://localhost:{DASHBOARD_PORT}")
    print(f"   {'─' * 35}\n")

    # Phase 1: Launch & Discover
    print("  Phase 1: Discovery...")
    ghost_log("cli", "phase_start", "Starting discovery", {"phase": "discovery"})

    pid = launch_app(app_name)
    time.sleep(3)

    app_graph = run_discovery(pid, app_name, scan_dir=scan_dir,
                              max_states=15, max_time_seconds=120)

    ghost_log("cli", "phase_end", "Discovery complete",
              {"phase": "discovery", "states": app_graph.get("total_states", 0)})
    print(f"   Found {app_graph.get('total_states', 0)} states, "
          f"{app_graph.get('total_elements', 0)} elements\n")

    # Phase 2: Generate test cases
    print("  Phase 2: Generating test cases...")
    ghost_log("cli", "phase_start", "Starting generation", {"phase": "generation"})

    demo_personas = ["hacker", "rusher", "edge_lord"]

    with open(PERSONAS_FILE) as f:
        all_personas = json.load(f)

    test_cases_by_persona = {}
    for persona_def in all_personas:
        if persona_def["id"] in demo_personas:
            tests = generate_tests(app_graph, persona_def, scan_dir)
            test_cases_by_persona[persona_def["id"]] = tests
            print(f"   {persona_def['name']}: {len(tests)} test cases")

    ghost_log("cli", "phase_end", "Generation complete", {"phase": "generation"})
    print()

    # Phase 3: Execute
    print("  Phase 3: Executing tests...")
    ghost_log("cli", "phase_start", "Starting execution", {"phase": "execution"})

    # Relaunch app fresh for clean state
    kill_app(pid)
    time.sleep(1)
    pid = launch_app(app_name)
    time.sleep(3)

    report = run_agents(
        app_name=app_name,
        test_cases_by_persona=test_cases_by_persona,
        app_graph=app_graph,
        scan_dir=scan_dir,
    )

    ghost_log("cli", "phase_end", "Execution complete", {"phase": "execution"})

    # Print summary
    print(f"\n{'=' * 50}")
    print(f"  Quest Results: {app_name}")
    print(f"{'=' * 50}")
    print(f"   Tests:  {report.get('total_tests', 0)}")
    print(f"   Pass:   {report.get('passed', 0)}")
    print(f"   Fail:   {report.get('failed', 0)}")
    print(f"   Report: {report.get('report_path', 'N/A')}")
    print(f"   Dashboard: http://localhost:{DASHBOARD_PORT}")
    print(f"{'=' * 50}\n")

    # Keep running for dashboard viewing
    print("Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        kill_app(pid)
        print("\nDone!")


def run_quick_test():
    """Quick smoke test -- runs discovery on TextEdit to verify the pipeline works."""
    ghost_log("system", "info", "Quick test mode")

    from quest.app_manager import launch_app, get_app_pid, kill_app
    from quest.scanner.ax_tree import get_ax_tree, get_interactable_elements
    from quest.scanner.interactions import screenshot, click
    from quest.config import get_scan_dir

    app_name = "TextEdit"
    scan_dir = str(get_scan_dir(app_name, "quicktest"))

    print("  Quick Test: Verifying core components...")

    # Test 1: App launch
    print("  1. Launching TextEdit...", end=" ")
    try:
        pid = launch_app(app_name)
        time.sleep(3)
        actual_pid = get_app_pid(app_name)
        assert actual_pid is not None, "Could not find PID"
        print(f"OK PID={actual_pid}")
    except Exception as e:
        print(f"FAIL {e}")
        return

    # Test 2: AX Tree
    print("  2. Reading accessibility tree...", end=" ")
    try:
        tree = get_ax_tree(actual_pid)
        assert tree is not None, "Tree is None"
        elements = get_interactable_elements(tree)
        print(f"OK {len(elements)} elements found")
        for el in elements[:5]:
            print(f"     - {el.get('role', '?')}: {el.get('title', '?')} @ {el.get('position', '?')}")
        if len(elements) > 5:
            print(f"     ... and {len(elements) - 5} more")
    except Exception as e:
        print(f"FAIL {e}")
        import traceback; traceback.print_exc()

    # Test 3: Screenshot
    print("  3. Taking screenshot...", end=" ")
    try:
        ss_path = os.path.join(scan_dir, "screenshots", "quicktest.png")
        screenshot(ss_path)
        assert os.path.exists(ss_path), f"Screenshot not saved to {ss_path}"
        size = os.path.getsize(ss_path)
        print(f"OK Saved ({size} bytes)")
    except Exception as e:
        print(f"FAIL {e}")
        import traceback; traceback.print_exc()

    # Test 4: Click
    print("  4. Testing click interaction...", end=" ")
    try:
        if elements:
            first_btn = next((e for e in elements if "Button" in e.get("role", "")), elements[0])
            pos = first_btn.get("position", [100, 100])
            sz = first_btn.get("size", [50, 30])
            cx = pos[0] + sz[0] // 2
            cy = pos[1] + sz[1] // 2
            click(cx, cy)
            print(f"OK Clicked '{first_btn.get('title', '?')}' at ({cx}, {cy})")
        else:
            click(200, 200)
            print("OK Clicked at (200, 200) -- no elements to target")
    except Exception as e:
        print(f"FAIL {e}")
        import traceback; traceback.print_exc()

    # Test 5: Logger
    print("  5. Testing logger...", end=" ")
    try:
        from quest.dashboard.logger import ghost_log, get_recent_logs
        ghost_log("system", "info", "Quick test log event", {"test": True})
        logs = get_recent_logs(5)
        assert len(logs) > 0, "No logs in buffer"
        print(f"OK {len(logs)} events in buffer")
    except Exception as e:
        print(f"FAIL {e}")

    # Test 6: Nebius API
    print("  6. Testing Nebius API...", end=" ")
    try:
        import requests
        from quest.config import NEBIUS_API_URL, NEBIUS_API_KEY, TEXT_MODEL

        if not NEBIUS_API_KEY:
            print("SKIP (no API key)")
        else:
            resp = requests.post(
                NEBIUS_API_URL,
                headers={
                    "Authorization": f"Bearer {NEBIUS_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": TEXT_MODEL,
                    "messages": [{"role": "user", "content": "Say 'hello' and nothing else."}],
                    "max_tokens": 10
                },
                timeout=15
            )
            resp.raise_for_status()
            reply = resp.json()["choices"][0]["message"]["content"]
            print(f"OK LLM replied: '{reply.strip()}'")
    except Exception as e:
        print(f"FAIL {e}")

    # Cleanup
    kill_app(pid)

    print(f"\n{'=' * 40}")
    print("Quick test complete!")
    print(f"{'=' * 40}\n")


def run_direct(app_name: str, persona_ids: list = None):
    """Run the full pipeline against a specific app."""
    from quest.app_manager import launch_app, kill_app
    from quest.scanner.mapper import run_discovery
    from quest.generator.test_generator import generate_tests
    from quest.executor.agent_runner import run_agents
    from quest.config import get_scan_dir

    scan_dir = str(get_scan_dir(app_name))

    print(f"\n  Launching {app_name}...")
    pid = launch_app(app_name)
    time.sleep(3)

    print("  Running discovery...")
    app_graph = run_discovery(pid, app_name, scan_dir=scan_dir)

    print("  Generating test cases...")
    with open(PERSONAS_FILE) as f:
        all_personas = json.load(f)

    if persona_ids:
        selected = [p for p in all_personas if p["id"] in persona_ids]
    else:
        selected = all_personas[:3]  # default to first 3

    test_cases_by_persona = {}
    for persona in selected:
        tests = generate_tests(app_graph, persona, scan_dir)
        test_cases_by_persona[persona["id"]] = tests
        print(f"   {persona['name']}: {len(tests)} tests")

    print("  Executing tests...")
    report = run_agents(app_name, test_cases_by_persona, app_graph, scan_dir)

    print(f"\n  Total: {report['total_tests']} | Pass: {report['passed']} | Fail: {report['failed']}")
    print(f"  Report: {report['report_path']}\n")


if __name__ == "__main__":
    main()
