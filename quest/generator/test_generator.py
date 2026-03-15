"""
Generates persona-driven test cases from an app graph using Nebius Token Factory LLM.
"""

import json
import os
import re
import requests

NEBIUS_API_URL = "https://api.studio.nebius.ai/v1/chat/completions"
NEBIUS_API_KEY = os.environ.get("NEBIUS_API_KEY")

TEST_GEN_SYSTEM_PROMPT = """You are an expert QA test engineer who specializes in \
persona-driven exploratory testing of macOS desktop applications.

You will receive:
1. An app graph describing all discovered states and UI elements of a macOS app
2. A persona description defining a specific type of user

Your job is to generate comprehensive test cases that this persona would naturally \
perform. Think about:
- How would this specific person USE this app?
- What mistakes would they make?
- What edge cases would they hit given their behavior patterns?
- What would they type into text fields?
- How would they navigate?
- What would frustrate them? What would they click repeatedly?

Generate between 5-15 test cases depending on app complexity.
Each test case should be a realistic sequence of actions.

CRITICAL: Your output must be a valid JSON array of test case objects.
Every action must reference real element IDs from the app graph or use coordinates.
Every test case must start from a known state in the app graph.

Available action types:
- "click": Click an element by ID
- "right_click": Right-click an element
- "double_click": Double-click an element
- "type": Type text into a focused element
- "key_press": Press a key (with optional modifiers)
- "drag": Drag from element/coords to end coords
- "scroll": Scroll at current position
- "coordinate_click": Click at raw screen coordinates
- "wait": Wait N seconds

Respond with ONLY a JSON array of test case objects. No other text."""


def generate_tests(app_graph: dict, persona: dict, scan_dir: str) -> list[dict]:
    """
    Main entry point. Generates test cases for a given persona against an app graph.
    """
    persona_id = persona["id"]
    output_path = os.path.join(scan_dir, f"test_cases_{persona_id}.json")

    if os.path.exists(output_path):
        print(f"Test cases already exist for {persona['name']}")
        with open(output_path, "r") as f:
            return json.load(f)

    print(f"Generating test cases for persona: {persona['name']}...")
    prompt = _build_llm_prompt(app_graph, persona)
    raw_response = _call_nebius_llm(prompt, TEST_GEN_SYSTEM_PROMPT)
    test_cases = _parse_test_cases(raw_response, persona)

    os.makedirs(scan_dir, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(test_cases, f, indent=2)

    print(f"Generated {len(test_cases)} test cases for {persona['name']}")
    return test_cases


def _build_llm_prompt(app_graph: dict, persona: dict) -> str:
    """
    Build the prompt to send to the LLM for test case generation.
    """
    # Summarize all states and their elements
    states_summary = []
    all_element_ids = []
    for state_name, state_data in app_graph.get("states", {}).items():
        elements_desc = []
        for elem in state_data.get("elements", []):
            all_element_ids.append(elem["id"])
            elem_line = (
                f"  - {elem['id']}: {elem['role']} \"{elem.get('title', '')}\" "
                f"— {elem.get('description', '')} | "
                f"actions: {elem.get('actions', [])} | "
                f"enabled: {elem.get('enabled', True)}"
            )
            if elem.get("value") is not None:
                elem_line += f" | current_value: \"{elem['value']}\""
            elements_desc.append(elem_line)

        transitions_desc = ""
        if state_data.get("transitions"):
            trans_lines = [
                f"  - {eid} → {target}"
                for eid, target in state_data["transitions"].items()
            ]
            transitions_desc = "\n  Transitions:\n" + "\n".join(trans_lines)

        states_summary.append(
            f"State: {state_name}\n"
            f"  Description: {state_data.get('description', '')}\n"
            f"  Elements:\n" + "\n".join(elements_desc) + transitions_desc
        )

    app_desc = (
        f"App: {app_graph.get('app_name', 'Unknown')}\n"
        f"Total states: {app_graph.get('total_states', len(app_graph.get('states', {})))}\n"
        f"Total elements: {app_graph.get('total_elements', len(all_element_ids))}\n\n"
        + "\n\n".join(states_summary)
    )

    persona_desc = (
        f"Persona ID: {persona['id']}\n"
        f"Name: {persona['name']}\n"
        f"Description: {persona.get('description', '')}\n"
        f"Behavior: {persona.get('behavior', '')}\n"
        f"Typing Speed: {persona.get('typing_speed', 'medium')}\n"
        f"Patience: {persona.get('patience', 'medium')}\n"
        f"Input Style: {persona.get('input_style', 'normal')}"
    )

    test_case_schema = json.dumps({
        "test_id": "test_{persona_id}_001",
        "persona_id": persona["id"],
        "persona_name": persona["name"],
        "title": "Short descriptive title",
        "description": "What this test verifies",
        "severity_if_fails": "critical|high|medium|low",
        "starting_state": "state_name_from_app_graph",
        "steps": [
            {
                "step_number": 1,
                "action": "click|right_click|double_click|type|key_press|drag|scroll|coordinate_click|wait",
                "target": "element_id or null",
                "coordinates": "null or [x, y]",
                "value": "null or text to type",
                "key": "null or key name",
                "modifiers": "null or [\"cmd\", \"shift\", etc]",
                "drag_end": "null or [x, y]",
                "scroll_direction": "null or up/down/left/right",
                "wait_seconds": "null or number",
                "expected_result": "What should happen",
                "failure_indicators": ["App crashes", "Error dialog appears"]
            }
        ],
        "cleanup_steps": [
            {
                "action": "key_press",
                "key": "escape",
                "modifiers": None
            }
        ]
    }, indent=2)

    return f"""=== APPLICATION GRAPH ===
{app_desc}

=== PERSONA ===
{persona_desc}

=== REQUIRED OUTPUT FORMAT ===
Return a JSON array where each object follows this exact schema:
{test_case_schema}

=== INSTRUCTIONS ===
Generate 5-15 test cases that "{persona['name']}" would naturally perform on this app.
Include a mix of:
- Happy path tests (normal usage in this persona's style)
- Negative tests (trying to break things based on persona behavior)
- Edge case tests (unusual but valid interactions)
- Navigation tests (exploring state transitions)
- Input validation tests (for all text fields, using persona's input style)
- Interaction combination tests (doing things in unexpected order)

Use ONLY element IDs that exist in the app graph above.
Use ONLY state names that exist in the app graph above.
Number test IDs sequentially: test_{persona['id']}_001, test_{persona['id']}_002, etc.
Set severity_if_fails appropriately based on impact.

Return ONLY the JSON array. No markdown, no explanation."""


def _call_nebius_llm(prompt: str, system_prompt: str) -> str:
    """
    Call Nebius Token Factory API.
    """
    if not NEBIUS_API_KEY:
        raise RuntimeError(
            "NEBIUS_API_KEY environment variable is not set. "
            "Please set it before generating test cases."
        )

    headers = {
        "Authorization": f"Bearer {NEBIUS_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "meta-llama/Llama-3.3-70B-Instruct",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 8000
    }

    response = requests.post(NEBIUS_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _parse_test_cases(llm_response: str, persona: dict) -> list[dict]:
    """
    Parse the LLM's response into structured test cases.
    Handles imperfect JSON from the LLM.
    """
    test_cases = None

    # Try direct JSON parse
    try:
        test_cases = json.loads(llm_response)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code blocks
    if test_cases is None:
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", llm_response, re.DOTALL)
        if match:
            try:
                test_cases = json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

    # Try finding the outermost JSON array
    if test_cases is None:
        match = re.search(r"\[.*\]", llm_response, re.DOTALL)
        if match:
            try:
                test_cases = json.loads(match.group(0))
            except json.JSONDecodeError:
                # Try fixing trailing commas
                cleaned = re.sub(r",\s*([\]}])", r"\1", match.group(0))
                try:
                    test_cases = json.loads(cleaned)
                except json.JSONDecodeError:
                    pass

    if test_cases is None:
        raise ValueError(
            f"Failed to parse LLM response as JSON. Raw response:\n{llm_response[:500]}"
        )

    # Wrap single object in a list
    if isinstance(test_cases, dict):
        test_cases = [test_cases]

    # Validate and normalize each test case
    required_fields = {
        "test_id", "persona_id", "persona_name", "title", "description",
        "severity_if_fails", "starting_state", "steps"
    }
    valid_severities = {"critical", "high", "medium", "low"}
    valid_actions = {
        "click", "right_click", "double_click", "type", "key_press",
        "drag", "scroll", "coordinate_click", "wait"
    }
    step_fields = {
        "step_number", "action", "target", "coordinates", "value",
        "key", "modifiers", "drag_end", "scroll_direction",
        "wait_seconds", "expected_result", "failure_indicators"
    }

    validated = []
    for i, tc in enumerate(test_cases):
        if not isinstance(tc, dict):
            continue

        # Fill in missing top-level fields
        tc.setdefault("test_id", f"test_{persona['id']}_{i + 1:03d}")
        tc.setdefault("persona_id", persona["id"])
        tc.setdefault("persona_name", persona["name"])
        tc.setdefault("title", f"Test case {i + 1}")
        tc.setdefault("description", "")
        tc.setdefault("severity_if_fails", "medium")
        tc.setdefault("starting_state", "state_0_main_window")
        tc.setdefault("steps", [])
        tc.setdefault("cleanup_steps", [])

        if tc["severity_if_fails"] not in valid_severities:
            tc["severity_if_fails"] = "medium"

        # Validate steps
        normalized_steps = []
        for j, step in enumerate(tc.get("steps", [])):
            if not isinstance(step, dict):
                continue
            step.setdefault("step_number", j + 1)
            step.setdefault("action", "click")
            step.setdefault("target", None)
            step.setdefault("coordinates", None)
            step.setdefault("value", None)
            step.setdefault("key", None)
            step.setdefault("modifiers", None)
            step.setdefault("drag_end", None)
            step.setdefault("scroll_direction", None)
            step.setdefault("wait_seconds", None)
            step.setdefault("expected_result", "Action completes successfully")
            step.setdefault("failure_indicators", ["App crashes", "App becomes unresponsive"])

            if step["action"] not in valid_actions:
                step["action"] = "click"

            normalized_steps.append(step)

        tc["steps"] = normalized_steps

        if tc["steps"]:
            validated.append(tc)

    if not validated:
        raise ValueError("No valid test cases could be parsed from LLM response.")

    return validated
