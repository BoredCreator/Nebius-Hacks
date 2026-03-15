"""
Screenshot analysis using Nebius Token Factory vision-capable LLM.
Identifies UI elements the accessibility tree might miss.

Set env var NEBIUS_API_KEY before use.
"""

import base64
import json
import os
from quest.dashboard.logger import ghost_log

import requests

NEBIUS_API_URL = "https://api.studio.nebius.ai/v1/chat/completions"
NEBIUS_VISION_MODEL = "Qwen/Qwen2.5-VL-72B-Instruct"
NEBIUS_TEXT_MODEL = "meta-llama/Llama-3.3-70B-Instruct"


def _get_nebius_key() -> str:
    key = os.environ.get("NEBIUS_API_KEY")
    if not key:
        raise RuntimeError(
            "NEBIUS_API_KEY env var not set. "
            "Export it before running: export NEBIUS_API_KEY=your_key"
        )
    return key


def _encode_image(path: str, max_dim: int = 1024) -> str:
    """Encode image to base64, resizing if needed to stay under API limits."""
    try:
        import subprocess
        # Use sips (built-in macOS) to check size and resize if needed
        result = subprocess.run(
            ["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
            capture_output=True, text=True,
        )
        w = h = 0
        for line in result.stdout.splitlines():
            if "pixelWidth" in line:
                w = int(line.split(":")[-1].strip())
            if "pixelHeight" in line:
                h = int(line.split(":")[-1].strip())

        if w > max_dim or h > max_dim:
            resized_path = path + ".resized.png"
            # Resize longest side to max_dim
            subprocess.run(
                ["sips", "--resampleHeightWidthMax", str(max_dim), path, "--out", resized_path],
                capture_output=True,
            )
            with open(resized_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            os.remove(resized_path)
            return data
    except Exception:
        pass

    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_screenshot(
    screenshot_path: str,
    ax_elements: list[dict],
    app_description: str = "",
    explored_states: list[str] = None,
) -> dict:
    """
    Send screenshot + accessibility tree to vision LLM.

    Returns:
    {
        "screen_description": str,
        "additional_elements": [
            {
                "description": str,
                "position": [x, y],
                "suggested_action": str,
                "confidence": float
            }
        ],
        "suggested_next_action": {
            "reasoning": str,
            "action": str,
            "target": str or None,
            "coordinates": [x, y] or None
        },
        "state_signature": str
    }
    """
    api_key = _get_nebius_key()

    # Build element summary for the prompt (strip internal refs)
    elem_summary = []
    for e in ax_elements:
        elem_summary.append({
            "id": e.get("id"),
            "role": e.get("role"),
            "title": e.get("title"),
            "description": e.get("description"),
            "position": e.get("position"),
            "size": e.get("size"),
            "actions": e.get("actions"),
            "enabled": e.get("enabled"),
        })

    explored_str = ", ".join(explored_states) if explored_states else "none yet"

    prompt = f"""Analyze this macOS application screenshot. The app is: {app_description or 'unknown'}.

Here are the UI elements already detected via the accessibility tree:
{json.dumps(elem_summary, indent=2)}

States already explored: {explored_str}

Your task:
1. Describe what you see on screen in 1-2 sentences.
2. Identify any interactive elements visible in the screenshot that are NOT in the accessibility tree list above (custom buttons, icons, canvas elements, etc.). For each, estimate its center position [x, y] on screen.
3. Suggest the best next action to explore this app (prioritize unexplored areas).
4. Provide a short unique signature for this screen state (e.g. "main_window_with_sidebar").

Respond with ONLY valid JSON matching this schema:
{{
    "screen_description": "...",
    "additional_elements": [
        {{"description": "...", "position": [x, y], "suggested_action": "click", "confidence": 0.8}}
    ],
    "suggested_next_action": {{
        "reasoning": "...",
        "action": "click|right_click|type|key_press|scroll|coordinate_click",
        "target": "elem_id or null",
        "coordinates": [x, y] // or null
    }},
    "state_signature": "..."
}}"""

    image_b64 = _encode_image(screenshot_path)

    payload = {
        "model": NEBIUS_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}"
                        },
                    },
                ],
            }
        ],
        "max_tokens": 2048,
        "temperature": 0.3,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    ghost_log("vision", "llm_call", "Analyzing screenshot", {"model": NEBIUS_VISION_MODEL},
              screenshot=screenshot_path)

    try:
        resp = requests.post(NEBIUS_API_URL, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        # Try to parse JSON from response (handle markdown code blocks)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        result = json.loads(content)
        ghost_log("vision", "llm_response", f"Screen: {result.get('state_signature', '?')}",
                  {"additional_elements": len(result.get("additional_elements", []))})
        return result
    except (requests.RequestException, json.JSONDecodeError, KeyError, IndexError) as e:
        ghost_log("vision", "error", f"LLM analysis failed: {e}")
        return {
            "screen_description": "Analysis failed",
            "additional_elements": [],
            "suggested_next_action": None,
            "state_signature": "unknown_state",
        }


def get_llm_decision(
    ax_elements: list[dict],
    screenshot_path: str,
    explored_states: dict,
    current_state: str,
    dfs_stack: list[str],
    app_name: str,
    interaction_history: list[dict],
) -> dict:
    """
    Ask the vision LLM to decide the next exploration action.

    Returns the decision JSON as specified in the DISCOVERY_SYSTEM_PROMPT.
    """
    api_key = _get_nebius_key()

    elem_summary = []
    for e in ax_elements:
        elem_summary.append({
            "id": e.get("id"),
            "role": e.get("role"),
            "title": e.get("title"),
            "description": e.get("description"),
            "position": e.get("position"),
            "size": e.get("size"),
            "actions": e.get("actions"),
            "enabled": e.get("enabled"),
        })

    # Build compact history (last 10 actions)
    recent_history = interaction_history[-10:] if interaction_history else []

    user_prompt = f"""App: {app_name}
Current state: {current_state}
DFS stack: {json.dumps(dfs_stack)}
Explored states: {json.dumps(list(explored_states.keys()))}

Accessibility tree elements:
{json.dumps(elem_summary, indent=2)}

Recent interaction history:
{json.dumps(recent_history, indent=2)}

Decide the NEXT ACTION. Respond with ONLY valid JSON:
{{
    "reasoning": "Why I'm choosing this action",
    "action_type": "click|right_click|double_click|type|key_press|drag|scroll|coordinate_click",
    "target": "elem_id or null",
    "coordinates": [x, y] // or null,
    "value": "text to type or null",
    "key": "key name or null",
    "modifiers": ["cmd", "shift"] // or null,
    "drag_end": [x, y] // or null,
    "scroll_direction": "up/down/left/right or null",
    "state_signature": "short description of current state",
    "is_new_state": true/false,
    "backtrack_suggestion": "How to get back or null"
}}"""

    system_prompt = """You are an expert macOS application explorer. Your job is to
systematically discover every screen, dialog, menu, and interactive element in a macOS
application through DFS exploration.

EXPLORATION RULES:
- Prioritize elements you haven't interacted with yet
- Always check the menu bar (File, Edit, View, etc.)
- Right-click elements to find hidden context menus
- If you see elements in the screenshot that aren't in the AX tree, use coordinate_click
- After exploring a submenu/dialog fully, backtrack to parent state
- Look for scroll areas and scroll to find hidden elements
- Try keyboard shortcuts you see listed in menus
- Mark a state as fully explored when all elements have been tried
- AVOID repeating the same action on the same element"""

    image_b64 = _encode_image(screenshot_path)

    payload = {
        "model": NEBIUS_VISION_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}"
                        },
                    },
                ],
            },
        ],
        "max_tokens": 1024,
        "temperature": 0.3,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    ghost_log("vision", "llm_call", "Getting exploration decision", {"model": NEBIUS_VISION_MODEL})

    try:
        resp = requests.post(NEBIUS_API_URL, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        decision = json.loads(content)
        ghost_log("vision", "llm_response", f"Decision: {decision.get('action_type', '?')}",
                  {"target": decision.get("target"), "reasoning": decision.get("reasoning", "")[:80]})
        return decision
    except (requests.RequestException, json.JSONDecodeError, KeyError, IndexError) as e:
        ghost_log("vision", "error", f"LLM decision failed: {e}")
        # Fallback: try first unexplored element
        if ax_elements:
            return {
                "reasoning": "LLM failed, trying first available element",
                "action_type": "click",
                "target": ax_elements[0].get("id"),
                "coordinates": None,
                "value": None,
                "key": None,
                "modifiers": None,
                "drag_end": None,
                "scroll_direction": None,
                "state_signature": "unknown",
                "is_new_state": False,
                "backtrack_suggestion": "press Escape",
            }
        return None
