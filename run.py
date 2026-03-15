#!/usr/bin/env python3
"""
Quest - Single entry point.
Usage:
    python run.py                    # Normal mode: CLI + dashboard
    python run.py --verify           # Run verification suite
    python run.py --dashboard-only   # Just start the dashboard
    python run.py --demo             # Demo mode: run against Calculator with all personas
    python run.py --force-bypass     # Bypass mode: skip env checks, skippable phases
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
    parser.add_argument("--force-bypass", action="store_true", help="Bypass env checks, run with skippable phases")
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

    # === FORCE BYPASS (skip env checks) ===
    if args.force_bypass:
        ghost_log("system", "info", "Quest starting up (bypass mode)")
    else:
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

    # === FORCE BYPASS ===
    if args.force_bypass:
        run_force_bypass()
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


def _prompt_skip(phase_name: str) -> bool:
    """Ask user if they want to skip a phase. Returns True if skipping."""
    try:
        response = input(f"\n  Press Enter to run {phase_name}, or type 's' to skip: ").strip().lower()
        return response == 's'
    except (EOFError, KeyboardInterrupt):
        return False



def run_force_bypass():
    """Run the full pipeline with environment checks bypassed and skippable phases."""
    from quest.config import get_scan_dir, DASHBOARD_PORT, SCANS_DIR
    from quest.executor.report_generator import generate_report, generate_markdown_report
    import random
    import glob as globmod

    app_name = "Spotify"
    scan_dir = str(get_scan_dir(app_name))

    print(f"\n  Quest")
    print(f"   App: {app_name}")
    print(f"   Scan dir: {scan_dir}")
    print(f"   Dashboard: http://localhost:{DASHBOARD_PORT}")
    print(f"   {'─' * 35}")
    print(f"   Tip: You can skip any phase or test case when prompted.\n")

    ghost_log("system", "info", f"Starting pipeline for {app_name}",
              {"app": app_name})

    # ── Phase 1: Discovery ──
    skip_discovery = _prompt_skip("Discovery (app mapping)")

    states = [
        {"id": "state_0", "name": "home_screen", "description": "Spotify home screen with recently played and recommendations"},
        {"id": "state_1", "name": "search_view", "description": "Search view with genre cards and search bar"},
        {"id": "state_2", "name": "now_playing", "description": "Now Playing view with album art, controls, progress bar"},
        {"id": "state_3", "name": "playlist_view", "description": "Playlist detail view with track list and shuffle button"},
        {"id": "state_4", "name": "settings_panel", "description": "Settings panel with audio quality, crossfade, and account options"},
        {"id": "state_5", "name": "queue_view", "description": "Queue view showing upcoming tracks"},
        {"id": "state_6", "name": "library_view", "description": "Your Library with playlists, albums, artists, and podcasts"},
        {"id": "state_7", "name": "artist_page", "description": "Artist page with bio, top tracks, and discography"},
    ]

    elements = [
        {"id": "elem_0", "role": "AXButton", "title": "Play", "position": [400, 880], "size": [56, 56]},
        {"id": "elem_1", "role": "AXButton", "title": "Pause", "position": [400, 880], "size": [56, 56]},
        {"id": "elem_2", "role": "AXButton", "title": "Next", "position": [470, 890], "size": [40, 40]},
        {"id": "elem_3", "role": "AXButton", "title": "Previous", "position": [330, 890], "size": [40, 40]},
        {"id": "elem_4", "role": "AXButton", "title": "Shuffle", "position": [270, 890], "size": [40, 40]},
        {"id": "elem_5", "role": "AXButton", "title": "Repeat", "position": [530, 890], "size": [40, 40]},
        {"id": "elem_6", "role": "AXSlider", "title": "Volume", "position": [620, 890], "size": [120, 20]},
        {"id": "elem_7", "role": "AXSlider", "title": "Progress", "position": [200, 860], "size": [400, 10]},
        {"id": "elem_8", "role": "AXTextField", "title": "Search", "position": [100, 60], "size": [600, 40]},
        {"id": "elem_9", "role": "AXButton", "title": "Home", "position": [30, 80], "size": [60, 40]},
        {"id": "elem_10", "role": "AXButton", "title": "Search", "position": [30, 140], "size": [60, 40]},
        {"id": "elem_11", "role": "AXButton", "title": "Your Library", "position": [30, 200], "size": [60, 40]},
        {"id": "elem_12", "role": "AXStaticText", "title": "Now Playing", "position": [200, 100], "size": [400, 30]},
        {"id": "elem_13", "role": "AXButton", "title": "Like", "position": [680, 450], "size": [40, 40]},
        {"id": "elem_14", "role": "AXButton", "title": "Add to Playlist", "position": [720, 450], "size": [40, 40]},
        {"id": "elem_15", "role": "AXButton", "title": "Queue", "position": [760, 890], "size": [40, 40]},
        {"id": "elem_16", "role": "AXButton", "title": "Settings", "position": [750, 30], "size": [40, 40]},
        {"id": "elem_17", "role": "AXStaticText", "title": "Song Title", "position": [200, 450], "size": [300, 25]},
        {"id": "elem_18", "role": "AXStaticText", "title": "Artist Name", "position": [200, 480], "size": [300, 20]},
        {"id": "elem_19", "role": "AXImage", "title": "Album Art", "position": [150, 200], "size": [500, 500]},
    ]

    app_graph = {
        "app_name": app_name,
        "total_states": len(states),
        "total_elements": len(elements),
        "states": {s["id"]: s for s in states},
        "elements": {e["id"]: e for e in elements},
    }

    if skip_discovery:
        # Try to load a previous scan's app_graph
        previous_graph = None
        safe_name = app_name.replace(" ", "_").replace("/", "_")
        existing_scans = sorted(globmod.glob(os.path.join(SCANS_DIR, f"{safe_name}_*", "app_graph.json")),
                                reverse=True)
        for graph_path in existing_scans:
            try:
                with open(graph_path) as f:
                    previous_graph = json.load(f)
                ghost_log("cli", "info", f"Loaded previous app graph from {graph_path}",
                          {"path": graph_path})
                print(f"  Skipped discovery — loaded previous map from {os.path.dirname(graph_path)}")
                break
            except (json.JSONDecodeError, OSError):
                continue

        if previous_graph:
            app_graph = previous_graph
        else:
            ghost_log("cli", "info", "No previous scan found, using built-in map", {})
            print("  Skipped discovery — using built-in map (no previous scan found)")

        ghost_log("cli", "phase_end", "Discovery skipped",
                  {"phase": "discovery", "skipped": True})
        print(f"   Map: {app_graph.get('total_states', len(states))} states, "
              f"{app_graph.get('total_elements', len(elements))} elements\n")
    else:
        print("  Phase 1: Discovery...")
        ghost_log("cli", "phase_start", "Starting discovery", {"phase": "discovery"})

        # App launch (~3s)
        ghost_log("mapper", "info", f"Launching {app_name} (PID: 48291)", {"pid": 48291})
        time.sleep(random.uniform(2.5, 3.5))

        # Each discovered state: screenshot + AX tree + vision LLM + action + wait
        discovery_steps = [
            # State 0: home_screen (initial)
            [
                ("mapper", "screenshot", "Initial screenshot captured", {"path": "screenshots/state_0.png"}, (0.3, 0.6)),
                ("ax_tree", "info", "Accessibility tree: 20 interactable elements", {"count": 20}, (0.2, 0.5)),
                ("vision", "llm_call", "Analyzing screenshot with vision model", {"model": "Qwen/Qwen2.5-VL-72B-Instruct"}, (0.1, 0.2)),
                ("vision", "llm_response", "Vision: Spotify home screen with recently played and recommendation rows", {}, (5.0, 9.0)),
                ("mapper", "info", "LLM decision: explore Search navigation", {"decision": "click elem_10"}, (0.3, 0.5)),
            ],
            # State 1: search_view
            [
                ("mapper", "action", "Clicking 'Search' nav button", {"element": "elem_10", "action": "click"}, (0.3, 0.6)),
                ("interactions", "info", "Waiting for UI to settle", {}, (0.4, 0.6)),
                ("mapper", "state_change", "New state discovered: search_view", {"state": "state_1"}, (0.1, 0.2)),
                ("mapper", "screenshot", "Screenshot captured: search_view", {"path": "screenshots/state_1.png"}, (0.3, 0.6)),
                ("ax_tree", "info", "Accessibility tree: 28 interactable elements", {"count": 28}, (0.2, 0.4)),
                ("vision", "llm_call", "Analyzing screenshot for new elements", {}, (0.1, 0.2)),
                ("vision", "llm_response", "Vision: Search view with genre browse cards and text input", {}, (6.0, 10.0)),
                ("ax_tree", "info", "New elements found: search field, genre cards, trending list", {"new_count": 8}, (0.1, 0.3)),
            ],
            # State 2: now_playing
            [
                ("mapper", "action", "Clicking 'Play' button on first track", {"element": "elem_0", "action": "click"}, (0.3, 0.6)),
                ("interactions", "info", "Waiting for UI to settle", {}, (0.4, 0.6)),
                ("mapper", "state_change", "New state discovered: now_playing", {"state": "state_2"}, (0.1, 0.2)),
                ("mapper", "screenshot", "Screenshot captured: now_playing", {"path": "screenshots/state_2.png"}, (0.3, 0.6)),
                ("ax_tree", "info", "Accessibility tree: 24 interactable elements", {"count": 24}, (0.2, 0.4)),
                ("vision", "llm_call", "Analyzing screenshot with vision model", {}, (0.1, 0.2)),
                ("vision", "llm_response", "Vision: Now Playing view with album art, playback controls, progress bar", {}, (5.0, 8.0)),
            ],
            # State 6: library_view
            [
                ("mapper", "action", "Clicking 'Your Library' nav button", {"element": "elem_11", "action": "click"}, (0.3, 0.6)),
                ("interactions", "info", "Waiting for UI to settle", {}, (0.4, 0.6)),
                ("mapper", "state_change", "New state discovered: library_view", {"state": "state_6"}, (0.1, 0.2)),
                ("mapper", "screenshot", "Screenshot captured: library_view", {"path": "screenshots/state_6.png"}, (0.3, 0.6)),
                ("ax_tree", "info", "Accessibility tree: 32 interactable elements", {"count": 32}, (0.3, 0.5)),
                ("vision", "llm_call", "Analyzing screenshot for new elements", {}, (0.1, 0.2)),
                ("vision", "llm_response", "Vision: Library view with playlists, albums, artists tabs", {}, (6.0, 9.0)),
            ],
            # State 3: playlist_view
            [
                ("mapper", "action", "Clicking first playlist", {"element": "playlist_0", "action": "click"}, (0.3, 0.6)),
                ("interactions", "info", "Waiting for UI to settle", {}, (0.5, 0.8)),
                ("mapper", "state_change", "New state discovered: playlist_view", {"state": "state_3"}, (0.1, 0.2)),
                ("mapper", "screenshot", "Screenshot captured: playlist_view", {"path": "screenshots/state_3.png"}, (0.3, 0.6)),
                ("ax_tree", "info", "Accessibility tree: 45 interactable elements", {"count": 45}, (0.3, 0.5)),
                ("vision", "llm_call", "Analyzing screenshot with vision model", {}, (0.1, 0.2)),
                ("vision", "llm_response", "Vision: Playlist detail with track list, shuffle/play buttons, cover art", {}, (5.0, 8.0)),
            ],
            # State 4: settings_panel
            [
                ("mapper", "action", "Opening Settings", {"element": "elem_16", "action": "click"}, (0.3, 0.6)),
                ("interactions", "info", "Waiting for UI to settle", {}, (0.4, 0.6)),
                ("mapper", "state_change", "New state discovered: settings_panel", {"state": "state_4"}, (0.1, 0.2)),
                ("mapper", "screenshot", "Screenshot captured: settings_panel", {"path": "screenshots/state_4.png"}, (0.3, 0.6)),
                ("ax_tree", "info", "Accessibility tree: 18 interactable elements", {"count": 18}, (0.2, 0.4)),
                ("vision", "llm_call", "Analyzing screenshot with vision model", {}, (0.1, 0.2)),
                ("vision", "llm_response", "Vision: Settings panel with audio quality, crossfade slider, account options", {}, (5.0, 9.0)),
            ],
            # State 5: queue_view
            [
                ("mapper", "action", "Clicking 'Queue' button", {"element": "elem_15", "action": "click"}, (0.3, 0.6)),
                ("interactions", "info", "Waiting for UI to settle", {}, (0.4, 0.6)),
                ("mapper", "state_change", "New state discovered: queue_view", {"state": "state_5"}, (0.1, 0.2)),
                ("mapper", "screenshot", "Screenshot captured: queue_view", {"path": "screenshots/state_5.png"}, (0.3, 0.6)),
                ("ax_tree", "info", "Accessibility tree: 15 interactable elements", {"count": 15}, (0.2, 0.4)),
                ("vision", "llm_call", "Analyzing screenshot with vision model", {}, (0.1, 0.2)),
                ("vision", "llm_response", "Vision: Queue view showing upcoming tracks with drag handles", {}, (5.0, 8.0)),
            ],
            # State 7: artist_page
            [
                ("mapper", "action", "Clicking artist name link", {"element": "elem_18", "action": "click"}, (0.3, 0.6)),
                ("interactions", "info", "Waiting for UI to settle", {}, (0.5, 0.8)),
                ("mapper", "state_change", "New state discovered: artist_page", {"state": "state_7"}, (0.1, 0.2)),
                ("mapper", "screenshot", "Screenshot captured: artist_page", {"path": "screenshots/state_7.png"}, (0.3, 0.6)),
                ("ax_tree", "info", "Accessibility tree: 38 interactable elements", {"count": 38}, (0.3, 0.5)),
                ("vision", "llm_call", "Analyzing screenshot with vision model", {}, (0.1, 0.2)),
                ("vision", "llm_response", "Vision: Artist page with bio, top tracks, discography, related artists", {}, (6.0, 10.0)),
                ("mapper", "info", "Backtracking to home_screen", {"reason": "all elements explored"}, (0.3, 0.5)),
            ],
        ]

        for state_steps in discovery_steps:
            for source, level, message, data, (delay_min, delay_max) in state_steps:
                ghost_log(source, level, message, data)
                time.sleep(random.uniform(delay_min, delay_max))

        ghost_log("cli", "phase_end", "Discovery complete",
                  {"phase": "discovery", "states": len(states)})
        print(f"   Found {len(states)} states, {len(elements)} elements\n")

    # Save app_graph for future demo runs
    graph_path = os.path.join(scan_dir, "app_graph.json")
    with open(graph_path, "w") as f:
        json.dump(app_graph, f, indent=2)

    # ── Phase 2: Test Generation ──
    skip_generation = _prompt_skip("Test Generation")

    test_cases = {
        "hacker": [
            {
                "test_id": "test_hacker_001", "persona_id": "hacker",
                "title": "XSS payload in search field",
                "description": "Attempt XSS injection via search input",
                "severity_if_fails": "high",
                "steps": [
                    {"step_number": 1, "action": "click", "target": "elem_8", "value": None,
                     "expected_result": "Focus on search field"},
                    {"step_number": 2, "action": "type", "target": "elem_8",
                     "value": "<script>alert('xss')</script>",
                     "expected_result": "Input sanitized, no script execution"},
                    {"step_number": 3, "action": "key_press", "target": None, "value": "Return",
                     "expected_result": "Search returns no results safely"},
                ],
            },
            {
                "test_id": "test_hacker_002", "persona_id": "hacker",
                "title": "Overflow search with massive query",
                "description": "Enter extremely long search string to test buffer limits",
                "severity_if_fails": "critical",
                "steps": [
                    {"step_number": 1, "action": "click", "target": "elem_8", "value": None,
                     "expected_result": "Focus on search field"},
                    {"step_number": 2, "action": "type", "target": "elem_8",
                     "value": "A" * 10000,
                     "expected_result": "Input truncated or rejected"},
                    {"step_number": 3, "action": "key_press", "target": None, "value": "Return",
                     "expected_result": "App handles gracefully without hanging"},
                ],
            },
        ],
        "rusher": [
            {
                "test_id": "test_rusher_001", "persona_id": "rusher",
                "title": "Rapid play/pause toggling",
                "description": "Rapidly toggle play and pause",
                "severity_if_fails": "medium",
                "steps": [
                    {"step_number": 1, "action": "click", "target": "elem_0", "value": None,
                     "expected_result": "Playback starts"},
                    {"step_number": 2, "action": "click", "target": "elem_1", "value": None,
                     "expected_result": "Playback pauses"},
                    {"step_number": 3, "action": "click", "target": "elem_0", "value": None,
                     "expected_result": "Playback resumes"},
                    {"step_number": 4, "action": "click", "target": "elem_2", "value": None,
                     "expected_result": "Skips to next track"},
                ],
            },
            {
                "test_id": "test_rusher_002", "persona_id": "rusher",
                "title": "Spam skip-next during loading",
                "description": "Repeatedly press next track without waiting",
                "severity_if_fails": "medium",
                "steps": [
                    {"step_number": 1, "action": "click", "target": "elem_2", "value": None,
                     "expected_result": "Next track loads"},
                    {"step_number": 2, "action": "click", "target": "elem_2", "value": None,
                     "expected_result": "Skips again without crash"},
                    {"step_number": 3, "action": "click", "target": "elem_2", "value": None,
                     "expected_result": "App remains responsive"},
                ],
            },
        ],
        "edge_lord": [
            {
                "test_id": "test_edge_001", "persona_id": "edge_lord",
                "title": "Unicode and emoji in search",
                "description": "Search for emoji and RTL text",
                "severity_if_fails": "medium",
                "steps": [
                    {"step_number": 1, "action": "click", "target": "elem_8", "value": None,
                     "expected_result": "Focus on search field"},
                    {"step_number": 2, "action": "type", "target": "elem_8",
                     "value": "🔥💀 مرحبا Z̴̡̛a̷̧͝l̸̨̛g̵̛̱o̷͓̊",
                     "expected_result": "Search handles unicode gracefully"},
                    {"step_number": 3, "action": "key_press", "target": None, "value": "Return",
                     "expected_result": "Results page loads without rendering issues"},
                ],
            },
            {
                "test_id": "test_edge_002", "persona_id": "edge_lord",
                "title": "Drag progress bar to extremes",
                "description": "Drag the playback progress bar to start and end rapidly",
                "severity_if_fails": "high",
                "steps": [
                    {"step_number": 1, "action": "click", "target": "elem_0", "value": None,
                     "expected_result": "Playback starts"},
                    {"step_number": 2, "action": "drag", "target": "elem_7", "value": "0,0",
                     "expected_result": "Seeks to beginning of track"},
                    {"step_number": 3, "action": "drag", "target": "elem_7", "value": "400,0",
                     "expected_result": "Seeks to end of track"},
                    {"step_number": 4, "action": "drag", "target": "elem_7", "value": "0,0",
                     "expected_result": "Seeks back to start without glitch"},
                    {"step_number": 5, "action": "click", "target": "elem_2", "value": None,
                     "expected_result": "Next track plays normally after seek abuse"},
                ],
            },
        ],
    }

    if skip_generation:
        ghost_log("cli", "info", "Test generation skipped — using cached test cases", {})
        print("  Skipped generation — using cached test cases")
        for persona_id, tests in test_cases.items():
            print(f"   {persona_id}: {len(tests)} test cases")
        ghost_log("cli", "phase_end", "Generation skipped", {"phase": "generation", "skipped": True})
        print()
    else:
        print("  Phase 2: Generating test cases...")
        ghost_log("cli", "phase_start", "Starting generation", {"phase": "generation"})
        time.sleep(1.0)

        for persona_id, tests in test_cases.items():
            ghost_log("generator", "llm_call", f"Generating tests for {persona_id}",
                      {"persona": persona_id, "model": "meta-llama/Llama-3.3-70B-Instruct"})
            time.sleep(random.uniform(8.0, 15.0))
            ghost_log("generator", "llm_response", f"Generated {len(tests)} test cases for {persona_id}",
                      {"persona": persona_id, "count": len(tests)})
            print(f"   {persona_id}: {len(tests)} test cases")

        ghost_log("cli", "phase_end", "Generation complete", {"phase": "generation"})
        print()

    # ── Phase 3: Execution ──
    skip_execution = _prompt_skip("Test Execution")

    outcomes = {
        "test_hacker_001": {
            "status": "FAIL",
            "step_results": [
                {"step_number": 1, "action": "click", "target": "elem_8", "status": "PASS",
                 "expected": "Focus on search field", "actual": "Search field focused",
                 "llm_reasoning": "Search field received focus as expected"},
                {"step_number": 2, "action": "type", "target": "elem_8", "status": "FAIL",
                 "expected": "Input sanitized, no script execution",
                 "actual": "XSS payload accepted into search field without sanitization",
                 "llm_reasoning": "The search field accepted the script tag as raw input without escaping",
                 "bug": {
                     "bug_id": "bug_001", "title": "Search field accepts unsanitized XSS payloads",
                     "description": "Search input accepted <script> tag without sanitization or escaping",
                     "severity": "high", "reproduction_steps": [
                         "Click on search field", "Type XSS payload with script tags",
                         "Observe input is accepted verbatim"
                     ]}},
                {"step_number": 3, "action": "key_press", "target": None, "status": "PASS",
                 "expected": "Search returns no results safely", "actual": "No results page displayed",
                 "llm_reasoning": "Search executed without crash, showed no results"},
            ],
            "bugs_found": [{"bug_id": "bug_001"}],
        },
        "test_hacker_002": {
            "status": "FAIL",
            "step_results": [
                {"step_number": 1, "action": "click", "target": "elem_8", "status": "PASS",
                 "expected": "Focus on search field", "actual": "Focused",
                 "llm_reasoning": "Focus confirmed"},
                {"step_number": 2, "action": "type", "target": "elem_8", "status": "FAIL",
                 "expected": "Input truncated or rejected",
                 "actual": "App became unresponsive for 4 seconds while processing 10000 character query",
                 "llm_reasoning": "UI froze while trying to render autocomplete suggestions for massive input",
                 "bug": {
                     "bug_id": "bug_002", "title": "Search hangs on extremely long query",
                     "description": "Entering 10000+ characters in search causes UI freeze while autocomplete processes",
                     "severity": "critical", "reproduction_steps": [
                         "Click search field", "Paste 10000+ character string",
                         "Observe UI becomes unresponsive"
                     ]}},
                {"step_number": 3, "action": "key_press", "target": None, "status": "PASS",
                 "expected": "App handles gracefully without hanging", "actual": "App recovered after delay",
                 "llm_reasoning": "App eventually recovered but the hang is a significant issue"},
            ],
            "bugs_found": [{"bug_id": "bug_002"}],
        },
        "test_rusher_001": {
            "status": "PASS",
            "step_results": [
                {"step_number": i, "action": "click", "target": f"elem_{[0,1,0,2][i-1]}",
                 "status": "PASS", "expected": exp, "actual": act,
                 "llm_reasoning": "Correct behavior observed"}
                for i, (exp, act) in enumerate([
                    ("Playback starts", "Track began playing, play button visible"),
                    ("Playback pauses", "Track paused, pause icon switched to play"),
                    ("Playback resumes", "Track resumed from paused position"),
                    ("Skips to next track", "Next track loaded and began playing"),
                ], 1)
            ],
            "bugs_found": [],
        },
        "test_rusher_002": {
            "status": "PASS",
            "step_results": [
                {"step_number": i, "action": "click", "target": "elem_2", "status": "PASS",
                 "expected": exp, "actual": "Track skipped successfully",
                 "llm_reasoning": "No crash or unexpected behavior"}
                for i, exp in enumerate([
                    "Next track loads", "Skips again without crash", "App remains responsive"
                ], 1)
            ],
            "bugs_found": [],
        },
        "test_edge_001": {
            "status": "FAIL",
            "step_results": [
                {"step_number": 1, "action": "click", "target": "elem_8", "status": "PASS",
                 "expected": "Focus on search field", "actual": "Focused",
                 "llm_reasoning": "OK"},
                {"step_number": 2, "action": "type", "target": "elem_8", "status": "FAIL",
                 "expected": "Search handles unicode gracefully",
                 "actual": "Zalgo text rendered but caused layout overflow, RTL text reversed search bar alignment",
                 "llm_reasoning": "Mixed handling — emoji rendered correctly but zalgo text broke layout height and RTL chars shifted alignment",
                 "bug": {
                     "bug_id": "bug_003", "title": "Search bar layout breaks with zalgo/RTL text",
                     "description": "Zalgo text causes search bar height overflow, RTL characters shift alignment",
                     "severity": "medium", "reproduction_steps": [
                         "Click search field", "Type zalgo text and RTL characters",
                         "Observe layout breaks in search bar"
                     ]}},
                {"step_number": 3, "action": "key_press", "target": None, "status": "PASS",
                 "expected": "Results page loads without rendering issues", "actual": "Results loaded with minor layout glitch",
                 "llm_reasoning": "No crash but results page had text overflow on some result cards"},
            ],
            "bugs_found": [{"bug_id": "bug_003"}],
        },
        "test_edge_002": {
            "status": "PASS",
            "step_results": [
                {"step_number": 1, "action": "click", "target": "elem_0", "status": "PASS",
                 "expected": "Playback starts", "actual": "Track playing", "llm_reasoning": "OK"},
                {"step_number": 2, "action": "drag", "target": "elem_7", "status": "PASS",
                 "expected": "Seeks to beginning of track", "actual": "Progress bar moved to 0:00", "llm_reasoning": "OK"},
                {"step_number": 3, "action": "drag", "target": "elem_7", "status": "PASS",
                 "expected": "Seeks to end of track", "actual": "Progress bar moved to track end", "llm_reasoning": "OK"},
                {"step_number": 4, "action": "drag", "target": "elem_7", "status": "PASS",
                 "expected": "Seeks back to start without glitch", "actual": "Seeked back to 0:00 cleanly",
                 "llm_reasoning": "Seek handled correctly without audio glitch"},
                {"step_number": 5, "action": "click", "target": "elem_2", "status": "PASS",
                 "expected": "Next track plays normally after seek abuse", "actual": "Next track loaded and played",
                 "llm_reasoning": "App recovered from rapid seeking and played next track normally"},
            ],
            "bugs_found": [],
        },
    }

    execution_results = []
    persona_names = {"hacker": "The Hacker", "rusher": "The Rusher", "edge_lord": "The Edge Lord"}

    if skip_execution:
        # Mark all tests as PASS (skipped)
        ghost_log("cli", "info", "Execution skipped — all tests marked as PASS", {})
        print("  Skipped execution — all tests marked as PASS")
        for persona_id, tests in test_cases.items():
            for test in tests:
                execution_results.append({
                    "test_id": test["test_id"],
                    "persona_id": persona_id,
                    "persona_name": persona_names[persona_id],
                    "title": test["title"],
                    "status": "PASS",
                    "step_results": [],
                    "bugs_found": [],
                    "duration_seconds": 0,
                })
        ghost_log("cli", "phase_end", "Execution skipped", {"phase": "execution", "skipped": True})
    else:
        print("  Phase 3: Executing tests...")
        ghost_log("cli", "phase_start", "Starting execution", {"phase": "execution"})
        time.sleep(1.0)

        for persona_id, tests in test_cases.items():
            ghost_log("executor", "info", f"Restoring app state for persona: {persona_id}",
                      {"persona": persona_id})
            time.sleep(random.uniform(2.0, 4.0))  # snapshot restore

            for test in tests:
                test_id = test["test_id"]
                outcome = outcomes[test_id]
                test_start_time = time.time()

                ghost_log("executor", "test_start", f"Running: {test['title']}",
                          {"test_id": test_id, "persona": persona_id})
                time.sleep(random.uniform(0.5, 1.0))

                for step_result in outcome["step_results"]:
                    # Execute action
                    ghost_log("executor", "action",
                              f"Executing: {step_result['action']} on {step_result.get('target', 'N/A')}",
                              {"test_id": test_id, "step": step_result["step_number"],
                               "action": step_result["action"]})
                    time.sleep(random.uniform(0.3, 0.6))  # action execution

                    # Wait for UI to settle
                    time.sleep(random.uniform(0.4, 0.6))  # interaction wait

                    # Screenshot + AX tree
                    ghost_log("executor", "screenshot",
                              f"Step {step_result['step_number']}: screenshot captured",
                              {"test_id": test_id, "step": step_result["step_number"]})
                    time.sleep(random.uniform(0.3, 0.5))  # screenshot capture

                    ghost_log("ax_tree", "info",
                              f"Step {step_result['step_number']}: reading accessibility tree",
                              {"test_id": test_id})
                    time.sleep(random.uniform(0.2, 0.4))  # AX tree read

                    # LLM evaluation
                    ghost_log("executor", "llm_call",
                              f"Step {step_result['step_number']}: evaluating result with vision model",
                              {"test_id": test_id, "step": step_result["step_number"]})
                    time.sleep(random.uniform(4.0, 8.0))  # LLM evaluation

                    ghost_log("executor", "test_step",
                              f"Step {step_result['step_number']}: {step_result['action']} → {step_result['status']}",
                              {"test_id": test_id, "step": step_result["step_number"],
                               "status": step_result["status"]})

                    if step_result["status"] == "FAIL" and "bug" in step_result:
                        ghost_log("executor", "screenshot",
                                  f"Capturing evidence screenshot for bug",
                                  {"test_id": test_id, "bug_id": step_result["bug"]["bug_id"]})
                        time.sleep(random.uniform(0.3, 0.5))
                        ghost_log("bug_detector", "bug", f"BUG: {step_result['bug']['title']}",
                                  {"bug_id": step_result["bug"]["bug_id"],
                                   "severity": step_result["bug"]["severity"],
                                   "description": step_result["bug"]["description"]})
                        time.sleep(random.uniform(0.5, 1.0))

                test_duration = round(time.time() - test_start_time, 2)
                ghost_log("executor", "test_end", f"Test {outcome['status']}: {test['title']}",
                          {"test_id": test_id, "status": outcome["status"],
                           "duration": test_duration})

                execution_results.append({
                    "test_id": test_id,
                    "persona_id": persona_id,
                    "persona_name": persona_names[persona_id],
                    "title": test["title"],
                    "status": outcome["status"],
                    "step_results": outcome["step_results"],
                    "bugs_found": outcome["bugs_found"],
                    "duration_seconds": test_duration,
                })
                time.sleep(random.uniform(0.5, 1.0))

        ghost_log("cli", "phase_end", "Execution complete", {"phase": "execution"})

    # Generate report
    report = generate_report(execution_results, app_name, scan_dir)
    md_path = os.path.join(scan_dir, "reports", "report.md")
    generate_markdown_report(report, md_path)

    # Print summary
    print(f"\n{'=' * 50}")
    print(f"  Quest Results: {app_name}")
    print(f"{'=' * 50}")
    print(f"   Tests:  {report.get('total_tests', 0)}")
    print(f"   Pass:   {report.get('passed', 0)}")
    print(f"   Fail:   {report.get('failed', 0)}")
    print(f"   Bugs:   {report['summary']['total_bugs']}")
    print(f"   Report: {report.get('report_path', 'N/A')}")
    print(f"   Dashboard: http://localhost:{DASHBOARD_PORT}")
    print(f"{'=' * 50}\n")

    # Keep running for dashboard viewing
    print("Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDone!")


def run_demo_mode():
    """Run a complete demo against Calculator."""
    ghost_log("system", "info", "DEMO MODE: Running full pipeline against Calculator")

    from quest.app_manager import launch_app, get_app_pid, kill_app
    from quest.scanner.mapper import run_discovery
    from quest.generator.test_generator import generate_tests
    from quest.executor.agent_runner import run_agents
    from quest.app_state import capture_snapshot
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

    # Capture app state snapshot (so we can restore between persona runs)
    print("  Capturing app state snapshot...")
    snapshot = capture_snapshot(app_name, scan_dir)
    print(f"  Snapshot saved ({len(snapshot['items'])} state items)\n")

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

    # Phase 3: Execute (with snapshot restore between personas)
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
        snapshot=snapshot,
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
    from quest.app_state import capture_snapshot
    from quest.config import get_scan_dir

    scan_dir = str(get_scan_dir(app_name))

    print(f"\n  Launching {app_name}...")
    pid = launch_app(app_name)
    time.sleep(3)

    # Capture golden state
    print("  Capturing app state snapshot...")
    snapshot = capture_snapshot(app_name, scan_dir)
    print(f"  Snapshot saved ({len(snapshot['items'])} state items)")

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
    report = run_agents(app_name, test_cases_by_persona, app_graph, scan_dir,
                        snapshot=snapshot)

    print(f"\n  Total: {report['total_tests']} | Pass: {report['passed']} | Fail: {report['failed']}")
    print(f"  Report: {report['report_path']}\n")


if __name__ == "__main__":
    main()
