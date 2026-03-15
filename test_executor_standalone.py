#!/usr/bin/env python3
"""Standalone test for the executor module using dummy data."""

import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from quest.executor.agent_runner import run_agents
from quest.executor.report_generator import generate_report, generate_markdown_report

# ---------------------------------------------------------------------------
# Dummy element map (flat lookup for coordinate resolution)
# ---------------------------------------------------------------------------
DUMMY_ELEMENT_MAP = {
    "elem_0": {"position": [100, 200], "size": [80, 30], "role": "AXButton", "title": "Play"},
    "elem_1": {"position": [200, 50], "size": [300, 30], "role": "AXTextField", "title": "Search"},
    "elem_2": {"position": [500, 20], "size": [60, 30], "role": "AXButton", "title": "Settings"},
    "elem_3": {"position": [10, 0], "size": [40, 20], "role": "AXMenuButton", "title": "File"},
    "elem_7": {"position": [20, 20], "size": [60, 30], "role": "AXButton", "title": "Back"},
    "elem_9": {"position": [10, 25], "size": [150, 20], "role": "AXMenuItem", "title": "New Playlist"},
    "elem_15": {"position": [100, 100], "size": [250, 30], "role": "AXTextField", "title": "Playlist Name"},
    "elem_16": {"position": [200, 160], "size": [80, 30], "role": "AXButton", "title": "Create"},
    "elem_18": {"position": [100, 250], "size": [200, 30], "role": "AXTextField", "title": "Display Name"},
    "elem_19": {"position": [300, 300], "size": [80, 30], "role": "AXButton", "title": "Save"},
    "elem_20": {"position": [190, 200], "size": [40, 30], "role": "AXButton", "title": "Next Track"},
    "elem_21": {"position": [50, 200], "size": [40, 30], "role": "AXButton", "title": "Previous Track"},
}

# ---------------------------------------------------------------------------
# Dummy app graph (the executor extracts element_map from this)
# ---------------------------------------------------------------------------
DUMMY_APP_GRAPH = {
    "app_name": "Spotify",
    "pid": 0,
    "timestamp": "2026-03-15T10:30:00",
    "total_states": 5,
    "total_elements": 23,
    "states": {
        "state_0_main_window": {
            "screenshot": "screenshots/state_0.png",
            "elements": [
                {"id": k, **v} for k, v in DUMMY_ELEMENT_MAP.items()
            ],
            "transitions": {},
        },
    },
}

# ---------------------------------------------------------------------------
# Dummy test cases
# ---------------------------------------------------------------------------
DUMMY_TEST_CASES = [
    {
        "test_id": "test_hacker_001",
        "persona_id": "hacker",
        "persona_name": "The Hacker",
        "title": "SQL Injection in Search Field",
        "description": "Attempt SQL injection payloads in the search text field",
        "severity_if_fails": "critical",
        "starting_state": "state_0_main_window",
        "steps": [
            {"step_number": 1, "action": "click", "target": "elem_1", "coordinates": None, "value": None, "key": None, "modifiers": None, "drag_end": None, "scroll_direction": None, "wait_seconds": None, "expected_result": "Search field is focused", "failure_indicators": ["App crashes"]},
            {"step_number": 2, "action": "type", "target": "elem_1", "coordinates": None, "value": "'; DROP TABLE users; --", "key": None, "modifiers": None, "drag_end": None, "scroll_direction": None, "wait_seconds": None, "expected_result": "Text entered, app handles it gracefully", "failure_indicators": ["App crashes", "Unhandled exception"]},
            {"step_number": 3, "action": "key_press", "target": None, "coordinates": None, "value": None, "key": "return", "modifiers": None, "drag_end": None, "scroll_direction": None, "wait_seconds": None, "expected_result": "Search executes, results shown", "failure_indicators": ["App crashes", "Blank screen"]},
        ],
        "cleanup_steps": [{"action": "key_press", "key": "escape", "modifiers": None}],
    },
    {
        "test_id": "test_rusher_001",
        "persona_id": "rusher",
        "persona_name": "The Rusher",
        "title": "Rapid Fire Play/Pause",
        "description": "Spam the play button as fast as possible",
        "severity_if_fails": "medium",
        "starting_state": "state_0_main_window",
        "steps": [
            {"step_number": 1, "action": "click", "target": "elem_0", "coordinates": None, "value": None, "key": None, "modifiers": None, "drag_end": None, "scroll_direction": None, "wait_seconds": None, "expected_result": "Playback starts", "failure_indicators": ["App crashes"]},
            {"step_number": 2, "action": "click", "target": "elem_0", "coordinates": None, "value": None, "key": None, "modifiers": None, "drag_end": None, "scroll_direction": None, "wait_seconds": None, "expected_result": "Playback pauses", "failure_indicators": ["App crashes"]},
            {"step_number": 3, "action": "click", "target": "elem_0", "coordinates": None, "value": None, "key": None, "modifiers": None, "drag_end": None, "scroll_direction": None, "wait_seconds": None, "expected_result": "Playback resumes", "failure_indicators": ["App crashes"]},
        ],
        "cleanup_steps": [],
    },
]


def main():
    scan_dir = "scans/test_execution"
    os.makedirs(os.path.join(scan_dir, "reports"), exist_ok=True)

    print("=" * 50)
    print("  AppGhost Executor — Standalone Test")
    print("=" * 50)

    report = run_agents(
        app_name="Spotify",
        test_cases_by_persona={
            "hacker": [DUMMY_TEST_CASES[0]],
            "rusher": [DUMMY_TEST_CASES[1]],
        },
        app_graph=DUMMY_APP_GRAPH,
        scan_dir=scan_dir,
    )

    print("\n" + "=" * 50)
    print("  RESULTS")
    print("=" * 50)
    print(f"  Total tests: {report['total_tests']}")
    print(f"  Passed:      {report['passed']}")
    print(f"  Failed:      {report['failed']}")
    print(f"  Report:      {report['report_path']}")

    md_path = os.path.join(scan_dir, "reports", "report.md")
    if os.path.isfile(md_path):
        print(f"\n--- Markdown Report ---\n")
        with open(md_path) as f:
            print(f.read())


if __name__ == "__main__":
    main()
