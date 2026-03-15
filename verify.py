#!/usr/bin/env python3
"""
Quest Verification Suite
Tests every interface contract between modules.
Run with: python run.py --verify
"""

import sys
import os
import json
import time
import traceback
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

results = {"passed": 0, "failed": 0, "skipped": 0, "errors": []}


def check(name, fn):
    """Run a single verification check."""
    print(f"  {'Testing':10} {name}...", end=" ", flush=True)
    try:
        result = fn()
        if result is True or result is None:
            print(f"{GREEN}PASS{RESET}")
            results["passed"] += 1
        elif result == "skip":
            print(f"{YELLOW}SKIP{RESET}")
            results["skipped"] += 1
        else:
            print(f"{RED}FAIL: {result}{RESET}")
            results["failed"] += 1
            results["errors"].append((name, str(result)))
    except Exception as e:
        print(f"{RED}ERROR: {e}{RESET}")
        results["failed"] += 1
        results["errors"].append((name, traceback.format_exc()))


def run_all_verifications():
    print(f"\n{BOLD}{'=' * 60}")
    print(f"Quest Verification Suite")
    print(f"{'=' * 60}{RESET}\n")

    # ==========================================
    print(f"{CYAN}[1/8] Config & Environment{RESET}")
    # ==========================================

    def check_config_imports():
        from quest.config import (NEBIUS_API_KEY, NEBIUS_API_URL, TEXT_MODEL,
                                  SCANS_DIR, PERSONAS_FILE, get_scan_dir, validate_environment)
        assert NEBIUS_API_URL is not None
        assert TEXT_MODEL is not None
    check("Config imports", check_config_imports)

    def check_env():
        from quest.config import validate_environment
        checks = validate_environment()
        failed = [name for name, (passed, _) in checks.items() if not passed]
        if failed:
            return f"Failed checks: {', '.join(failed)}"
    check("Environment validation", check_env)

    def check_personas_file():
        from quest.config import PERSONAS_FILE
        assert os.path.isfile(PERSONAS_FILE), f"Not found: {PERSONAS_FILE}"
        with open(PERSONAS_FILE) as f:
            personas = json.load(f)
        assert isinstance(personas, list), "personas.json should be a list"
        assert len(personas) > 0, "No personas defined"
        required_keys = {"id", "name", "description", "behavior"}
        for p in personas:
            missing = required_keys - set(p.keys())
            assert not missing, f"Persona '{p.get('id', '?')}' missing keys: {missing}"
    check("Personas file", check_personas_file)

    def check_scan_dir_creation():
        from quest.config import get_scan_dir
        test_dir = get_scan_dir("VerifyTest", "verify_000")
        assert test_dir.exists()
        assert (test_dir / "screenshots").exists()
        assert (test_dir / "evidence").exists()
        assert (test_dir / "reports").exists()
        import shutil
        shutil.rmtree(test_dir)
    check("Scan directory creation", check_scan_dir_creation)

    print()

    # ==========================================
    print(f"{CYAN}[2/8] Dashboard Logger{RESET}")
    # ==========================================

    def check_logger_import():
        from quest.dashboard.logger import ghost_log, get_recent_logs, get_stats
    check("Logger imports", check_logger_import)

    def check_logger_emit():
        from quest.dashboard.logger import ghost_log, get_recent_logs
        event = ghost_log("system", "info", "Verification test event",
                          {"test": True, "timestamp": datetime.now().isoformat()})
        assert isinstance(event, dict)
        assert event["source"] == "system"
        assert event["level"] == "info"
        assert event["message"] == "Verification test event"
        assert event["data"]["test"] is True
        recent = get_recent_logs(5, source="system")
        assert len(recent) > 0
        assert any(e["message"] == "Verification test event" for e in recent)
    check("Logger emit & retrieve", check_logger_emit)

    def check_logger_filtering():
        from quest.dashboard.logger import ghost_log, get_recent_logs
        ghost_log("mapper", "action", "verify_filter_test_1")
        ghost_log("executor", "bug", "verify_filter_test_2")
        mapper_logs = get_recent_logs(100, source="mapper")
        assert all(l["source"] == "mapper" for l in mapper_logs)
        bug_logs = get_recent_logs(100, level="bug")
        assert all(l["level"] == "bug" for l in bug_logs)
    check("Logger filtering", check_logger_filtering)

    def check_logger_stats():
        from quest.dashboard.logger import get_stats
        stats = get_stats()
        assert "total_events" in stats
        assert "by_source" in stats
        assert "by_level" in stats
        assert isinstance(stats["total_events"], int)
    check("Logger stats", check_logger_stats)

    print()

    # ==========================================
    print(f"{CYAN}[3/8] App Manager{RESET}")
    # ==========================================

    def check_app_manager_imports():
        from quest.app_manager import list_applications, launch_app, get_app_pid, kill_app
    check("App manager imports", check_app_manager_imports)

    def check_list_applications():
        from quest.app_manager import list_applications
        apps = list_applications()
        assert isinstance(apps, list), f"Expected list, got {type(apps)}"
        assert len(apps) > 0, "No applications found"
        app_names_lower = [a.lower() for a in apps]
        assert any("calculator" in a for a in app_names_lower), "Calculator not found in apps"
    check("List applications", check_list_applications)

    def check_launch_and_kill():
        from quest.app_manager import launch_app, get_app_pid, kill_app
        pid = launch_app("Calculator")
        assert pid is not None, "launch_app returned None"
        time.sleep(2)
        found_pid = get_app_pid("Calculator")
        assert found_pid is not None, "get_app_pid returned None after launch"
        kill_app(found_pid)
        time.sleep(1)
    check("Launch & kill app", check_launch_and_kill)

    print()

    # ==========================================
    print(f"{CYAN}[4/8] Scanner / Mapper{RESET}")
    # ==========================================

    def check_scanner_imports():
        from quest.scanner.ax_tree import get_ax_tree, get_interactable_elements
        from quest.scanner.interactions import screenshot, click, right_click, type_text, key_press, scroll, drag
        from quest.scanner.mapper import run_discovery
    check("Scanner imports", check_scanner_imports)

    def check_ax_tree():
        from quest.app_manager import launch_app, get_app_pid, kill_app
        from quest.scanner.ax_tree import get_ax_tree, get_interactable_elements

        pid = launch_app("Calculator")
        time.sleep(2)
        actual_pid = get_app_pid("Calculator")

        tree = get_ax_tree(actual_pid)
        assert tree is not None, "AX tree is None"
        assert isinstance(tree, dict), f"Expected dict, got {type(tree)}"

        elements = get_interactable_elements(tree)
        assert isinstance(elements, list), f"Expected list, got {type(elements)}"
        assert len(elements) > 0, "No interactable elements found in Calculator"

        required_keys = {"id", "role", "position", "actions"}
        for elem in elements[:3]:
            missing = required_keys - set(elem.keys())
            assert not missing, f"Element missing keys: {missing}. Element: {elem}"
            assert isinstance(elem["position"], (list, tuple)), f"Position should be list, got {type(elem['position'])}"
            assert len(elem["position"]) == 2, f"Position should have 2 values, got {len(elem['position'])}"

        kill_app(actual_pid)
        time.sleep(1)
    check("AX tree reading", check_ax_tree)

    def check_screenshot():
        from quest.scanner.interactions import screenshot
        import tempfile
        path = os.path.join(tempfile.gettempdir(), "quest_verify_ss.png")
        screenshot(path)
        assert os.path.exists(path), f"Screenshot not saved to {path}"
        size = os.path.getsize(path)
        assert size > 1000, f"Screenshot too small ({size} bytes)"
        os.remove(path)
    check("Screenshot capture", check_screenshot)

    def check_interactions():
        from quest.scanner.interactions import click, right_click, type_text, key_press, scroll
        assert callable(click)
        assert callable(right_click)
        assert callable(type_text)
        assert callable(key_press)
        assert callable(scroll)
    check("Interaction functions exist", check_interactions)

    print()

    # ==========================================
    print(f"{CYAN}[5/8] Test Generator{RESET}")
    # ==========================================

    def check_generator_imports():
        from quest.generator.test_generator import generate_tests, _build_llm_prompt
    check("Generator imports", check_generator_imports)

    def check_generator_prompt_build():
        from quest.generator.test_generator import _build_llm_prompt
        dummy_graph = {
            "app_name": "TestApp",
            "total_states": 1,
            "total_elements": 2,
            "states": {
                "state_0": {
                    "elements": [
                        {"id": "e0", "role": "AXButton", "title": "OK", "description": "",
                         "position": [10, 10], "size": [50, 30], "actions": ["AXPress"],
                         "value": None, "enabled": True},
                    ],
                    "transitions": {}
                }
            }
        }
        persona = {"id": "test", "name": "Test", "description": "test", "behavior": "test"}
        prompt = _build_llm_prompt(dummy_graph, persona)
        assert isinstance(prompt, str)
        assert len(prompt) > 50
        assert "TestApp" in prompt
    check("Generator prompt building", check_generator_prompt_build)

    print()

    # ==========================================
    print(f"{CYAN}[6/8] Executor{RESET}")
    # ==========================================

    def check_executor_imports():
        from quest.executor.agent_runner import run_agents, execute_test_case, execute_step
        from quest.executor.bug_detector import check_crash, check_hang, get_memory_usage, detect_memory_leak
        from quest.executor.report_generator import generate_report, generate_markdown_report
    check("Executor imports", check_executor_imports)

    def check_bug_detector():
        from quest.executor.bug_detector import get_memory_usage, detect_memory_leak
        our_pid = os.getpid()
        mem = get_memory_usage(our_pid)
        assert isinstance(mem, int), f"Expected int, got {type(mem)}"
        assert mem > 0, "Memory usage should be > 0 for our own process"
        assert detect_memory_leak([100, 100, 100, 100]) is False
        assert detect_memory_leak([100, 120, 140, 160]) is True  # 60% growth
        assert detect_memory_leak([100, 105, 110, 115]) is False  # 15% growth
    check("Bug detector", check_bug_detector)

    def check_report_generator():
        from quest.executor.report_generator import generate_report, generate_markdown_report
        from quest.config import get_scan_dir
        scan_dir = str(get_scan_dir("TestApp", "verify_report"))
        dummy_results = [
            {
                "test_id": "test_001", "persona_id": "hacker", "persona_name": "The Hacker",
                "title": "Test Input Validation", "status": "FAIL",
                "started_at": "2026-03-15T11:00:00", "ended_at": "2026-03-15T11:00:10",
                "duration_seconds": 10,
                "step_results": [
                    {"step_number": 1, "status": "PASS", "action": "click"},
                    {"step_number": 2, "status": "FAIL", "action": "type",
                     "bug": {"bug_id": "bug_001", "severity": "high",
                             "title": "Input not sanitized",
                             "description": "App accepts script tags",
                             "reproduction_steps": ["Type <script>", "Click submit"],
                             "screenshot": None}}
                ],
                "bugs_found": ["bug_001"]
            },
            {
                "test_id": "test_002", "persona_id": "rusher", "persona_name": "The Rusher",
                "title": "Rapid Clicking", "status": "PASS",
                "started_at": "2026-03-15T11:00:10", "ended_at": "2026-03-15T11:00:15",
                "duration_seconds": 5,
                "step_results": [{"step_number": 1, "status": "PASS", "action": "click"}],
                "bugs_found": []
            }
        ]
        report = generate_report(dummy_results, "TestApp", scan_dir)
        assert isinstance(report, dict)
        assert "summary" in report
        assert report["summary"]["total_tests"] == 2
        assert report["summary"]["passed"] == 1
        assert report["summary"]["failed"] == 1
        assert report["summary"]["total_bugs"] >= 1

        md_path = os.path.join(scan_dir, "reports", "report.md")
        generate_markdown_report(report, md_path)
        assert os.path.exists(md_path), "Markdown report not created"
        md_content = open(md_path).read()
        assert len(md_content) > 100, "Report seems too short"

        import shutil
        shutil.rmtree(scan_dir, ignore_errors=True)
    check("Report generation", check_report_generator)

    print()

    # ==========================================
    print(f"{CYAN}[7/8] Dashboard Server{RESET}")
    # ==========================================

    def check_dashboard_imports():
        from quest.dashboard.server import app
        from fastapi.testclient import TestClient
    check("Dashboard imports", check_dashboard_imports)

    def check_dashboard_endpoints():
        from quest.dashboard.server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)

        resp = client.get("/")
        assert resp.status_code == 200, f"/ returned {resp.status_code}"

        endpoints = ["/api/logs", "/api/stats", "/api/scans",
                     "/api/bugs", "/api/llm_calls", "/api/pipeline_status"]
        for endpoint in endpoints:
            resp = client.get(endpoint)
            assert resp.status_code == 200, f"{endpoint} returned {resp.status_code}"
            data = resp.json()
            assert isinstance(data, dict), f"{endpoint} didn't return dict"
    check("Dashboard API endpoints", check_dashboard_endpoints)

    def check_dashboard_websocket():
        from quest.dashboard.server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        with client.websocket_connect("/ws/logs") as ws:
            from quest.dashboard.logger import ghost_log
            ghost_log("system", "info", "websocket_verify_test")
            # Connection working is the main test
    check("Dashboard WebSocket", check_dashboard_websocket)

    print()

    # ==========================================
    print(f"{CYAN}[8/8] End-to-End Data Flow{RESET}")
    # ==========================================

    def check_data_flow_graph_to_generator():
        from quest.generator.test_generator import _build_llm_prompt
        graph = {
            "app_name": "DataFlowTest", "total_states": 1, "total_elements": 2,
            "states": {
                "state_0": {
                    "elements": [
                        {"id": "e0", "role": "AXButton", "title": "Test",
                         "description": "", "position": [10, 10], "size": [50, 30],
                         "actions": ["AXPress"], "value": None, "enabled": True},
                    ],
                    "transitions": {}
                }
            }
        }
        persona = {"id": "test", "name": "Test", "description": "test", "behavior": "test"}
        prompt = _build_llm_prompt(graph, persona)
        assert isinstance(prompt, str)
        assert len(prompt) > 50
        assert "DataFlowTest" in prompt
    check("Graph -> Generator data flow", check_data_flow_graph_to_generator)

    def check_element_map_extraction():
        from quest.executor.agent_runner import _build_element_map
        graph = {
            "states": {
                "s0": {
                    "elements": [
                        {"id": "e0", "position": [10, 20], "size": [30, 40], "role": "AXButton", "title": "A"},
                        {"id": "e1", "position": [50, 60], "size": [70, 80], "role": "AXTextField", "title": "B"},
                    ]
                },
                "s1": {
                    "elements": [
                        {"id": "e2", "position": [90, 100], "size": [110, 120], "role": "AXButton", "title": "C"},
                        {"id": "e0", "position": [10, 20], "size": [30, 40], "role": "AXButton", "title": "A"},
                    ]
                }
            }
        }
        element_map = _build_element_map(graph)
        assert len(element_map) == 3, f"Expected 3 unique elements, got {len(element_map)}"
        assert "e0" in element_map
        assert "e1" in element_map
        assert "e2" in element_map
    check("Element map extraction from graph", check_element_map_extraction)

    print()

    # ==========================================
    # SUMMARY
    # ==========================================
    total = results["passed"] + results["failed"] + results["skipped"]

    print(f"\n{BOLD}{'=' * 60}")
    print(f"VERIFICATION RESULTS")
    print(f"{'=' * 60}{RESET}")
    print(f"  {GREEN}Passed:  {results['passed']}{RESET}")
    print(f"  {RED}Failed:  {results['failed']}{RESET}")
    print(f"  {YELLOW}Skipped: {results['skipped']}{RESET}")
    print(f"  Total:    {total}")

    if results["errors"]:
        print(f"\n{RED}{BOLD}FAILURES:{RESET}")
        for name, error in results["errors"]:
            print(f"\n  {RED}x {name}{RESET}")
            error_lines = error.strip().split("\n")
            for line in error_lines[:5]:
                print(f"    {line}")
            if len(error_lines) > 5:
                print(f"    ... ({len(error_lines) - 5} more lines)")

    if results["failed"] == 0:
        print(f"\n{GREEN}{BOLD}ALL CHECKS PASSED{RESET}")
    else:
        print(f"\n{RED}{BOLD}{results['failed']} CHECK(S) FAILED{RESET}")

    return results["failed"] == 0


if __name__ == "__main__":
    success = run_all_verifications()
    sys.exit(0 if success else 1)
