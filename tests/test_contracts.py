"""
Contract tests: verify that the data structures each module produces
match what the next module in the pipeline expects.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Shared test data ────────────────────────────────────────────────────

SAMPLE_APP_GRAPH = {
    "app_name": "ContractTestApp",
    "pid": 12345,
    "timestamp": "2026-03-15T12:00:00",
    "total_states": 2,
    "total_elements": 4,
    "states": {
        "state_0_main": {
            "screenshot": "screenshots/state_0.png",
            "description": "Main window",
            "elements": [
                {"id": "elem_0", "role": "AXButton", "title": "Submit",
                 "description": "Submit form", "position": [100, 200],
                 "size": [80, 30], "actions": ["AXPress"],
                 "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_1", "role": "AXTextField", "title": "Name",
                 "description": "Enter name", "position": [100, 100],
                 "size": [200, 30], "actions": ["AXConfirm"],
                 "value": "", "enabled": True, "source": "ax_tree"},
            ],
            "transitions": {"elem_0": "state_1_result"},
        },
        "state_1_result": {
            "screenshot": "screenshots/state_1.png",
            "description": "Result page",
            "elements": [
                {"id": "elem_2", "role": "AXStaticText", "title": "Result",
                 "description": "", "position": [100, 100],
                 "size": [200, 30], "actions": [],
                 "value": "Hello", "enabled": True, "source": "ax_tree"},
                {"id": "elem_3", "role": "AXButton", "title": "Back",
                 "description": "", "position": [100, 200],
                 "size": [80, 30], "actions": ["AXPress"],
                 "value": None, "enabled": True, "source": "ax_tree"},
            ],
            "transitions": {"elem_3": "state_0_main"},
        },
    },
}

SAMPLE_PERSONA = {
    "id": "contract_tester",
    "name": "Contract Tester",
    "description": "A tester for contract verification",
    "behavior": "Normal usage",
    "typing_speed": "medium",
    "patience": "medium",
    "input_style": "normal",
}

SAMPLE_TEST_CASE = {
    "test_id": "test_contract_001",
    "persona_id": "contract_tester",
    "persona_name": "Contract Tester",
    "title": "Basic submit flow",
    "description": "Test the submit button",
    "severity_if_fails": "medium",
    "starting_state": "state_0_main",
    "steps": [
        {
            "step_number": 1, "action": "click", "target": "elem_0",
            "coordinates": None, "value": None, "key": None,
            "modifiers": None, "drag_end": None, "scroll_direction": None,
            "wait_seconds": None,
            "expected_result": "Form submits",
            "failure_indicators": ["Error dialog"],
        },
        {
            "step_number": 2, "action": "type", "target": "elem_1",
            "coordinates": None, "value": "hello", "key": None,
            "modifiers": None, "drag_end": None, "scroll_direction": None,
            "wait_seconds": None,
            "expected_result": "Text entered",
            "failure_indicators": ["App crashes"],
        },
    ],
    "cleanup_steps": [],
}


# ── Contract: app_graph -> generator ────────────────────────────────────

class TestMapperToGenerator:
    """Mapper output must be consumable by the generator."""

    def test_graph_has_required_keys(self):
        required = {"app_name", "total_states", "total_elements", "states"}
        assert required.issubset(SAMPLE_APP_GRAPH.keys())

    def test_states_have_elements(self):
        for sid, state in SAMPLE_APP_GRAPH["states"].items():
            assert "elements" in state, f"State {sid} missing 'elements'"
            assert isinstance(state["elements"], list)

    def test_elements_have_required_fields(self):
        required = {"id", "role", "position", "actions"}
        for state in SAMPLE_APP_GRAPH["states"].values():
            for elem in state["elements"]:
                missing = required - set(elem.keys())
                assert not missing, f"Element {elem.get('id')} missing: {missing}"

    def test_generator_accepts_graph(self):
        from quest.generator.test_generator import _build_llm_prompt
        prompt = _build_llm_prompt(SAMPLE_APP_GRAPH, SAMPLE_PERSONA)
        assert isinstance(prompt, str)
        assert "ContractTestApp" in prompt
        assert "elem_0" in prompt


# ── Contract: generator -> executor ─────────────────────────────────────

class TestGeneratorToExecutor:
    """Generator output must be consumable by the executor."""

    def test_test_case_has_required_keys(self):
        required = {"test_id", "persona_id", "title", "steps"}
        assert required.issubset(SAMPLE_TEST_CASE.keys())

    def test_steps_have_required_fields(self):
        required = {"step_number", "action", "expected_result"}
        for step in SAMPLE_TEST_CASE["steps"]:
            missing = required - set(step.keys())
            assert not missing, f"Step {step.get('step_number')} missing: {missing}"

    def test_valid_actions(self):
        valid = {"click", "right_click", "double_click", "type", "key_press",
                 "drag", "scroll", "coordinate_click", "wait"}
        for step in SAMPLE_TEST_CASE["steps"]:
            assert step["action"] in valid, f"Invalid action: {step['action']}"

    def test_executor_element_map_from_graph(self):
        from quest.executor.agent_runner import _build_element_map
        emap = _build_element_map(SAMPLE_APP_GRAPH)
        # All targets in test case steps should resolve
        for step in SAMPLE_TEST_CASE["steps"]:
            if step.get("target"):
                assert step["target"] in emap, f"Target {step['target']} not in element map"


# ── Contract: executor -> report_generator ──────────────────────────────

class TestExecutorToReporter:
    """Executor results must be consumable by report_generator."""

    SAMPLE_RESULT = {
        "test_id": "test_001", "persona_id": "hacker",
        "persona_name": "Hacker", "title": "Injection test",
        "status": "FAIL",
        "started_at": "2026-03-15T11:00:00",
        "ended_at": "2026-03-15T11:00:10",
        "duration_seconds": 10,
        "step_results": [
            {"step_number": 1, "status": "PASS", "action": "click"},
            {"step_number": 2, "status": "FAIL", "action": "type",
             "bug": {"bug_id": "bug_001", "severity": "high",
                     "title": "Vuln", "description": "desc",
                     "reproduction_steps": ["step1"],
                     "screenshot": None}},
        ],
        "bugs_found": ["bug_001"],
    }

    def test_result_has_required_keys(self):
        required = {"test_id", "persona_id", "status", "step_results", "bugs_found"}
        assert required.issubset(self.SAMPLE_RESULT.keys())

    def test_report_generator_accepts_results(self):
        from quest.executor.report_generator import generate_report
        from quest.config import get_scan_dir
        import shutil

        scan_dir = str(get_scan_dir("ContractTest", "contract_rpt"))
        report = generate_report([self.SAMPLE_RESULT], "ContractTestApp", scan_dir)
        assert report["summary"]["total_tests"] == 1
        assert report["summary"]["failed"] == 1
        assert report["summary"]["total_bugs"] >= 1
        shutil.rmtree(scan_dir, ignore_errors=True)
