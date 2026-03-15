"""
Integration tests for Quest pipeline.
Tests that modules can import each other and data flows correctly.
"""

import json
import os
import sys
import shutil

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Config ──────────────────────────────────────────────────────────────

def test_config_imports():
    from quest.config import (
        NEBIUS_API_KEY, NEBIUS_API_URL, TEXT_MODEL, VISION_MODEL,
        SCANS_DIR, PERSONAS_FILE, get_scan_dir, validate_environment,
    )
    assert NEBIUS_API_URL is not None
    assert TEXT_MODEL is not None
    assert VISION_MODEL is not None


def test_scan_dir_creation():
    from quest.config import get_scan_dir
    d = get_scan_dir("IntegTest", "test_000")
    assert d.exists()
    assert (d / "screenshots").exists()
    assert (d / "evidence").exists()
    assert (d / "reports").exists()
    shutil.rmtree(d)


def test_personas_file_valid():
    from quest.config import PERSONAS_FILE
    assert os.path.isfile(PERSONAS_FILE)
    with open(PERSONAS_FILE) as f:
        personas = json.load(f)
    assert isinstance(personas, list)
    assert len(personas) > 0
    for p in personas:
        assert "id" in p
        assert "name" in p
        assert "description" in p
        assert "behavior" in p


# ── Logger ──────────────────────────────────────────────────────────────

def test_logger_roundtrip():
    from quest.dashboard.logger import ghost_log, get_recent_logs
    ghost_log("system", "info", "pytest_roundtrip", {"key": "val"})
    logs = get_recent_logs(10, source="system")
    assert any(l["message"] == "pytest_roundtrip" for l in logs)


def test_logger_stats():
    from quest.dashboard.logger import get_stats
    stats = get_stats()
    assert "total_events" in stats
    assert isinstance(stats["total_events"], int)


# ── App Manager ─────────────────────────────────────────────────────────

def test_list_applications():
    from quest.app_manager import list_applications
    apps = list_applications()
    assert isinstance(apps, list)
    assert len(apps) > 0


# ── Generator ───────────────────────────────────────────────────────────

def test_generator_prompt_build():
    from quest.generator.test_generator import _build_llm_prompt
    graph = {
        "app_name": "PytestApp", "total_states": 1, "total_elements": 1,
        "states": {
            "state_0": {
                "elements": [
                    {"id": "e0", "role": "AXButton", "title": "OK",
                     "description": "", "position": [10, 10], "size": [50, 30],
                     "actions": ["AXPress"], "value": None, "enabled": True}
                ],
                "transitions": {}
            }
        }
    }
    persona = {"id": "test", "name": "Test", "description": "d", "behavior": "b"}
    prompt = _build_llm_prompt(graph, persona)
    assert "PytestApp" in prompt
    assert "e0" in prompt


# ── Bug Detector ────────────────────────────────────────────────────────

def test_memory_leak_detection():
    from quest.executor.bug_detector import detect_memory_leak
    assert detect_memory_leak([100, 100, 100]) is False
    assert detect_memory_leak([100, 200, 300]) is True
    assert detect_memory_leak([]) is False
    assert detect_memory_leak([100]) is False


def test_get_memory_usage_self():
    from quest.executor.bug_detector import get_memory_usage
    mem = get_memory_usage(os.getpid())
    assert mem > 0


# ── Report Generator ────────────────────────────────────────────────────

def test_report_generation():
    from quest.executor.report_generator import generate_report, generate_markdown_report
    from quest.config import get_scan_dir

    scan_dir = str(get_scan_dir("PytestReport", "test_report"))
    results = [
        {"test_id": "t1", "persona_id": "p1", "persona_name": "P1",
         "title": "T1", "status": "PASS",
         "started_at": "2026-01-01T00:00:00", "ended_at": "2026-01-01T00:00:05",
         "duration_seconds": 5,
         "step_results": [{"step_number": 1, "status": "PASS", "action": "click"}],
         "bugs_found": []},
    ]
    report = generate_report(results, "PytestApp", scan_dir)
    assert report["summary"]["total_tests"] == 1
    assert report["summary"]["passed"] == 1

    md_path = os.path.join(scan_dir, "reports", "report.md")
    generate_markdown_report(report, md_path)
    assert os.path.exists(md_path)

    shutil.rmtree(scan_dir, ignore_errors=True)


# ── Element Map ─────────────────────────────────────────────────────────

def test_element_map_building():
    from quest.executor.agent_runner import _build_element_map
    graph = {
        "states": {
            "s0": {"elements": [
                {"id": "e0", "position": [10, 20], "size": [30, 40]},
                {"id": "e1", "position": [50, 60], "size": [70, 80]},
            ]},
            "s1": {"elements": [
                {"id": "e0", "position": [10, 20], "size": [30, 40]},  # dup
                {"id": "e2", "position": [90, 100], "size": [110, 120]},
            ]},
        }
    }
    emap = _build_element_map(graph)
    assert len(emap) == 3
    assert set(emap.keys()) == {"e0", "e1", "e2"}


# ── Dashboard ───────────────────────────────────────────────────────────

def test_dashboard_endpoints():
    from quest.dashboard.server import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    assert client.get("/").status_code == 200
    for ep in ["/api/logs", "/api/stats", "/api/scans", "/api/bugs",
               "/api/llm_calls", "/api/pipeline_status"]:
        resp = client.get(ep)
        assert resp.status_code == 200, f"{ep} returned {resp.status_code}"
        assert isinstance(resp.json(), dict)
