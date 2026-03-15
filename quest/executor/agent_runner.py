"""
Executes test cases against a running macOS app.

For each test step:
1. Execute the action (click, type, etc.)
2. Wait briefly for the app to respond
3. Take a screenshot
4. Read the AX tree
5. Send screenshot + AX tree + expected result to LLM
6. LLM determines: PASS, FAIL, or INCONCLUSIVE
7. If FAIL: record bug with evidence
8. If app crashes: record critical bug, skip remaining steps
"""

import json
import os
import time
import base64
from datetime import datetime

from quest.scanner import interactions, ax_tree
from quest.executor.bug_detector import check_crash, check_hang, get_memory_usage, detect_memory_leak


# ---------------------------------------------------------------------------
# LLM evaluation prompt
# ---------------------------------------------------------------------------

STEP_EVAL_SYSTEM_PROMPT = """You are an expert QA engineer evaluating whether a
test step on a macOS application passed or failed.

You will receive:
1. A screenshot of the app after an action was performed
2. The accessibility tree state after the action
3. What action was performed
4. What was expected to happen
5. What failure indicators to look for

Evaluate the result and respond with JSON only (no markdown fencing):
{
    "status": "PASS" | "FAIL" | "INCONCLUSIVE",
    "actual_result": "Description of what you observe in the screenshot",
    "reasoning": "Why you determined this status",
    "bug_detected": true/false,
    "bug_description": "Description of the bug if detected" | null,
    "bug_severity": "critical" | "high" | "medium" | "low" | null
}

Be strict about failures. Look for:
- Error dialogs or messages
- UI elements in wrong state
- Missing expected content
- Visual glitches or broken layouts
- Any indication the app didn't respond as expected
"""


# ---------------------------------------------------------------------------
# Nebius LLM helper
# ---------------------------------------------------------------------------

def _call_llm(system_prompt: str, user_prompt: str, image_path: str | None = None) -> dict:
    """Call Nebius-hosted LLM for step evaluation. Returns parsed JSON dict."""
    import requests

    api_key = os.environ.get("NEBIUS_API_KEY", "")
    api_url = os.environ.get(
        "NEBIUS_API_URL",
        "https://api.studio.nebius.com/v1/chat/completions",
    )
    model = os.environ.get("NEBIUS_MODEL", "Qwen/Qwen2.5-VL-72B-Instruct")

    messages = [{"role": "system", "content": system_prompt}]

    # Build user message (optionally with image)
    user_content: list[dict] = []
    if image_path and os.path.isfile(image_path):
        try:
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            })
        except Exception:
            pass  # skip image if unreadable

    user_content.append({"type": "text", "text": user_prompt})
    messages.append({"role": "user", "content": user_content})

    try:
        resp = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": model, "messages": messages, "temperature": 0.1},
            timeout=60,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        # Strip markdown code fences if present
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        return json.loads(text.strip())
    except Exception as exc:
        return {
            "status": "INCONCLUSIVE",
            "actual_result": f"LLM call failed: {exc}",
            "reasoning": "Could not reach LLM for evaluation",
            "bug_detected": False,
            "bug_description": None,
            "bug_severity": None,
        }


# ---------------------------------------------------------------------------
# Element resolution
# ---------------------------------------------------------------------------

def _build_element_map(app_graph: dict) -> dict:
    """Flatten all states' elements into an {elem_id: info} lookup."""
    element_map: dict = {}
    for state in app_graph.get("states", {}).values():
        for elem in state.get("elements", []):
            element_map[elem["id"]] = elem
    return element_map


# ---------------------------------------------------------------------------
# Step execution
# ---------------------------------------------------------------------------

def execute_step(step: dict, element_map: dict, pid: int) -> None:
    """Execute a single step action against the running app."""
    action = step["action"]
    target = step.get("target")
    coords = step.get("coordinates")

    # Resolve target element to coordinates
    x, y = None, None
    if target and target in element_map:
        elem = element_map[target]
        x = elem["position"][0] + elem["size"][0] // 2
        y = elem["position"][1] + elem["size"][1] // 2
    elif coords:
        x, y = coords

    if action == "click":
        interactions.click(x, y)
    elif action == "right_click":
        interactions.right_click(x, y)
    elif action == "double_click":
        interactions.double_click(x, y)
    elif action == "type":
        interactions.type_text(step.get("value", ""))
    elif action == "key_press":
        interactions.key_press(step.get("key", ""), step.get("modifiers"))
    elif action == "drag":
        end = step.get("drag_end", [0, 0])
        interactions.drag(x, y, end[0], end[1])
    elif action == "scroll":
        interactions.scroll(x, y, step.get("scroll_direction", "down"))
    elif action == "coordinate_click":
        if coords:
            interactions.click(coords[0], coords[1])
    elif action == "wait":
        time.sleep(step.get("wait_seconds", 1))


# ---------------------------------------------------------------------------
# Step evaluation
# ---------------------------------------------------------------------------

def evaluate_step_result(screenshot_path: str, ax_state: dict,
                         step: dict, test_context: str) -> dict:
    """Ask the LLM whether a step passed or failed."""
    user_prompt = (
        f"Test context: {test_context}\n"
        f"Action performed: {step['action']}"
    )
    if step.get("target"):
        user_prompt += f" on {step['target']}"
    if step.get("value"):
        user_prompt += f" with value: {step['value'][:200]}"
    if step.get("key"):
        mods = "+".join(step["modifiers"]) + "+" if step.get("modifiers") else ""
        user_prompt += f" key: {mods}{step['key']}"

    user_prompt += (
        f"\n\nExpected result: {step.get('expected_result', 'N/A')}\n"
        f"Failure indicators: {step.get('failure_indicators', [])}\n"
        f"Accessibility tree (partial): {json.dumps(ax_state, default=str)[:2000]}\n"
    )

    return _call_llm(STEP_EVAL_SYSTEM_PROMPT, user_prompt, screenshot_path)


# ---------------------------------------------------------------------------
# App liveness check
# ---------------------------------------------------------------------------

def check_app_alive(pid: int) -> bool:
    """Check if the app process is still running."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Single test-case execution
# ---------------------------------------------------------------------------

def execute_test_case(test_case: dict, app_name: str, pid: int,
                      element_map: dict, evidence_dir: str) -> dict:
    """Execute a single test case and return the result dict."""
    test_id = test_case["test_id"]
    test_evidence_dir = os.path.join(evidence_dir, test_id)
    os.makedirs(test_evidence_dir, exist_ok=True)

    started_at = datetime.now()
    step_results: list[dict] = []
    bugs_found: list[str] = []
    bug_counter = 0
    memory_readings: list[int] = []
    overall_status = "PASS"

    test_context = (
        f"App: {app_name} | Test: {test_case.get('title', test_id)} | "
        f"Persona: {test_case.get('persona_name', 'unknown')} | "
        f"Description: {test_case.get('description', '')}"
    )

    for step in test_case.get("steps", []):
        step_num = step["step_number"]
        print(f"    Step {step_num}: {step['action']}", end="")
        if step.get("target"):
            print(f" -> {step['target']}", end="")
        print()

        # Record memory before step
        mem = get_memory_usage(pid)
        if mem > 0:
            memory_readings.append(mem)

        # 1. Execute the action
        try:
            execute_step(step, element_map, pid)
        except Exception as exc:
            step_results.append({
                "step_number": step_num,
                "action": step["action"],
                "target": step.get("target"),
                "status": "ERROR",
                "screenshot": None,
                "expected": step.get("expected_result"),
                "actual": f"Action execution error: {exc}",
                "llm_reasoning": None,
            })
            overall_status = "ERROR"
            break

        # 2. Brief wait for app to react
        time.sleep(0.5)

        # 3. Check if app is still alive
        if not check_app_alive(pid):
            crash_info = check_crash(pid)
            bug_counter += 1
            bug_id = f"bug_{test_id}_{bug_counter:03d}"
            bug = {
                "bug_id": bug_id,
                "severity": "critical",
                "title": f"App crashed during: {test_case.get('title', test_id)}",
                "description": (
                    f"The application crashed after step {step_num} "
                    f"({step['action']}). Crash info: {crash_info}"
                ),
                "reproduction_steps": _build_repro_steps(test_case, step_num),
                "screenshot": None,
            }
            step_results.append({
                "step_number": step_num,
                "action": step["action"],
                "target": step.get("target"),
                "status": "FAIL",
                "screenshot": None,
                "expected": step.get("expected_result"),
                "actual": "Application crashed",
                "llm_reasoning": "Process is no longer running — app crashed.",
                "bug": bug,
            })
            bugs_found.append(bug_id)
            overall_status = "FAIL"
            break

        # 4. Check for hang
        if check_hang(pid):
            bug_counter += 1
            bug_id = f"bug_{test_id}_{bug_counter:03d}"
            bug = {
                "bug_id": bug_id,
                "severity": "high",
                "title": f"App hung during: {test_case.get('title', test_id)}",
                "description": f"The application became unresponsive after step {step_num}.",
                "reproduction_steps": _build_repro_steps(test_case, step_num),
                "screenshot": None,
            }
            step_results.append({
                "step_number": step_num,
                "action": step["action"],
                "target": step.get("target"),
                "status": "FAIL",
                "screenshot": None,
                "expected": step.get("expected_result"),
                "actual": "Application is not responding",
                "llm_reasoning": "AX query timed out — app appears hung.",
                "bug": bug,
            })
            bugs_found.append(bug_id)
            overall_status = "FAIL"
            break

        # 5. Take screenshot
        screenshot_path = os.path.join(test_evidence_dir, f"step_{step_num}.png")
        interactions.screenshot(screenshot_path)

        # 6. Read AX tree
        ax_state = ax_tree.get_ax_tree(pid)

        # 7. Evaluate with LLM
        eval_result = evaluate_step_result(screenshot_path, ax_state, step, test_context)

        step_status = eval_result.get("status", "INCONCLUSIVE")

        step_record: dict = {
            "step_number": step_num,
            "action": step["action"],
            "target": step.get("target"),
            "status": step_status,
            "screenshot": screenshot_path,
            "expected": step.get("expected_result"),
            "actual": eval_result.get("actual_result", ""),
            "llm_reasoning": eval_result.get("reasoning", ""),
        }

        if eval_result.get("bug_detected"):
            bug_counter += 1
            bug_id = f"bug_{test_id}_{bug_counter:03d}"
            step_record["bug"] = {
                "bug_id": bug_id,
                "severity": eval_result.get("bug_severity", test_case.get("severity_if_fails", "medium")),
                "title": eval_result.get("bug_description", f"Failure at step {step_num}"),
                "description": eval_result.get("bug_description", ""),
                "reproduction_steps": _build_repro_steps(test_case, step_num),
                "screenshot": screenshot_path,
            }
            bugs_found.append(bug_id)

        step_results.append(step_record)

        if step_status == "FAIL":
            overall_status = "FAIL"
            # Continue remaining steps unless it's a crash — might find more bugs

    # Check for memory leak across the test
    if detect_memory_leak(memory_readings):
        bug_counter += 1
        bug_id = f"bug_{test_id}_{bug_counter:03d}"
        bugs_found.append(bug_id)
        step_results.append({
            "step_number": 0,
            "action": "memory_check",
            "target": None,
            "status": "FAIL",
            "screenshot": None,
            "expected": "Stable memory usage",
            "actual": f"Memory grew from {memory_readings[0]} to {memory_readings[-1]} bytes",
            "llm_reasoning": "Memory leak detected via RSS monitoring.",
            "bug": {
                "bug_id": bug_id,
                "severity": "high",
                "title": f"Possible memory leak during: {test_case.get('title', test_id)}",
                "description": (
                    f"RSS memory grew from {memory_readings[0]} to "
                    f"{memory_readings[-1]} bytes during test execution."
                ),
                "reproduction_steps": _build_repro_steps(test_case, len(test_case.get("steps", []))),
                "screenshot": None,
            },
        })

    # Run cleanup steps
    for cleanup in test_case.get("cleanup_steps", []):
        try:
            execute_step(cleanup, element_map, pid)
        except Exception:
            pass

    ended_at = datetime.now()

    return {
        "test_id": test_id,
        "persona_id": test_case.get("persona_id", "unknown"),
        "persona_name": test_case.get("persona_name", "Unknown"),
        "title": test_case.get("title", test_id),
        "status": overall_status,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "duration_seconds": round((ended_at - started_at).total_seconds(), 2),
        "step_results": step_results,
        "bugs_found": bugs_found,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_repro_steps(test_case: dict, up_to_step: int) -> list[str]:
    """Build human-readable reproduction steps up to the given step number."""
    repro: list[str] = []
    for step in test_case.get("steps", []):
        if step["step_number"] > up_to_step:
            break
        desc = f"{step['step_number']}. {step['action']}"
        if step.get("target"):
            desc += f" on {step['target']}"
        if step.get("value"):
            desc += f": {step['value'][:100]}"
        if step.get("key"):
            mods = "+".join(step["modifiers"]) + "+" if step.get("modifiers") else ""
            desc += f": {mods}{step['key']}"
        repro.append(desc)
    return repro


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_agents(app_name: str, test_cases_by_persona: dict,
               app_graph: dict, scan_dir: str) -> dict:
    """
    Execute all test cases for all personas.

    Args:
        app_name: Name of the app under test.
        test_cases_by_persona: {"hacker": [test_cases], "rusher": [...], ...}
        app_graph: Full app graph from the scanner/mapper.
        scan_dir: Directory to save evidence and reports.

    Returns:
        Full execution report dict.
    """
    evidence_dir = os.path.join(scan_dir, "evidence")
    os.makedirs(evidence_dir, exist_ok=True)

    element_map = _build_element_map(app_graph)

    # Try to get PID of the running app (fall back to 0 for stub mode)
    from quest.app_manager import get_app_pid
    pid = get_app_pid(app_name) or 0

    all_results: list[dict] = []

    for persona_id, test_cases in test_cases_by_persona.items():
        print(f"\n  === Persona: {persona_id} ({len(test_cases)} tests) ===\n")
        for tc in test_cases:
            print(f"  [{tc['test_id']}] {tc.get('title', tc['test_id'])}")
            result = execute_test_case(tc, app_name, pid, element_map, evidence_dir)
            status_icon = {"PASS": "+", "FAIL": "!", "ERROR": "x"}.get(result["status"], "?")
            print(f"    -> [{status_icon}] {result['status']} ({result['duration_seconds']}s, {len(result['bugs_found'])} bugs)\n")
            all_results.append(result)

    # Generate report
    from quest.executor.report_generator import generate_report, generate_markdown_report

    report = generate_report(all_results, app_name, scan_dir)
    md_path = os.path.join(scan_dir, "reports", "report.md")
    generate_markdown_report(report, md_path)

    print(f"  Report saved to {scan_dir}/reports/")

    return report
