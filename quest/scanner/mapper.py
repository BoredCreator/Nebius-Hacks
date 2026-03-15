"""
Main DFS discovery engine for macOS app exploration.

Autonomously crawls a running app by combining the accessibility tree,
screenshots, and an LLM vision model to build a complete app graph.
"""

import json
import os
import time
from datetime import datetime
from quest.dashboard.logger import ghost_log

from quest.scanner.ax_tree import get_ax_tree, get_interactable_elements, perform_ax_action
from quest.scanner.interactions import (
    screenshot,
    click,
    double_click,
    right_click,
    drag,
    scroll,
    type_text,
    key_press,
    get_focused_window_bounds,
    focus_app,
)
from quest.scanner.vision import analyze_screenshot, get_llm_decision


def _elements_signature(elements: list[dict]) -> str:
    """Create a signature from element roles, titles, and count for state dedup.

    Deliberately ignores 'value' because many apps (especially Electron apps
    like Spotify, Discord) have dynamic values that change every frame
    (timers, progress bars, now-playing text) which would make every read
    look like a new state.  The structural layout (roles + titles + count)
    is a much more stable indicator of which screen we're on.
    """
    parts = []
    for e in elements:
        role = e.get("role", "")
        title = e.get("title", "") or ""
        enabled = "1" if e.get("enabled", True) else "0"
        parts.append(f"{role}:{title}:{enabled}")
    parts.sort()
    return f"n={len(parts)}|" + "|".join(parts)


def _save_screenshot(scan_dir: str, state_index: int, pid: int) -> str:
    """Take and save a screenshot for a state."""
    ss_dir = os.path.join(scan_dir, "screenshots")
    os.makedirs(ss_dir, exist_ok=True)
    path = os.path.join(ss_dir, f"state_{state_index}.png")
    screenshot(path, pid=pid)
    return path


def _is_within_bounds(coords: list, bounds: dict) -> bool:
    """Return True if [x, y] falls inside the app window bounds."""
    if not coords or not bounds:
        return True  # can't check, allow
    x, y = coords[0], coords[1]
    return (
        bounds["x"] <= x <= bounds["x"] + bounds["width"]
        and bounds["y"] <= y <= bounds["y"] + bounds["height"]
    )


def _filter_elements_to_window(elements: list[dict], bounds: dict) -> list[dict]:
    """Remove elements whose position is outside the app window."""
    if not bounds:
        return elements
    result = []
    for e in elements:
        pos = e.get("position")
        if pos:
            if _is_within_bounds(pos, bounds):
                result.append(e)
        else:
            result.append(e)
    return result


def _execute_action(decision: dict, elements_by_id: dict, window_bounds: dict = None, pid: int = None) -> bool:
    """Execute an interaction based on the LLM decision. Returns False if blocked."""
    action_type = decision.get("action_type", "click")
    target = decision.get("target")
    coords = decision.get("coordinates")
    value = decision.get("value")
    key = decision.get("key")
    modifiers = decision.get("modifiers")
    drag_end = decision.get("drag_end")
    scroll_dir = decision.get("scroll_direction")

    # Resolve coordinates from element if needed
    if target and target in elements_by_id and not coords:
        elem = elements_by_id[target]
        pos = elem.get("position", [0, 0])
        size = elem.get("size", [0, 0])
        if pos and pos != [0, 0]:
            coords = [pos[0] + size[0] // 2, pos[1] + size[1] // 2]

    # Block any action whose coordinates land outside the app window
    if coords and window_bounds and not _is_within_bounds(coords, window_bounds):
        ghost_log("interactions", "warning",
                  f"Blocked out-of-window action at {coords} (window: {window_bounds})")
        return False

    # For AX-based actions, try the AX action first (only for real AX elements, not vision)
    if target and target in elements_by_id and action_type == "click":
        elem = elements_by_id[target]
        if elem.get("source") != "vision":
            ax_ref = elem.get("_ax_element")
            actions = elem.get("actions", [])
            if ax_ref and "AXPress" in actions:
                if perform_ax_action(ax_ref, "AXPress"):
                    ghost_log("interactions", "action", f"AX Pressed {target} ({elem.get('title', '?')})")
                    return True

    if action_type in ("click", "coordinate_click"):
        if coords:
            ghost_log("interactions", "action", f"Click at ({coords[0]}, {coords[1]})")
            click(coords[0], coords[1], pid=pid)
        else:
            ghost_log("interactions", "warning", f"No valid coordinates for click on {target}")
            return False
    elif action_type == "right_click":
        if coords:
            ghost_log("interactions", "action", f"Right-click at ({coords[0]}, {coords[1]})")
            right_click(coords[0], coords[1], pid=pid)
    elif action_type == "double_click":
        if coords:
            ghost_log("interactions", "action", f"Double-click at ({coords[0]}, {coords[1]})")
            double_click(coords[0], coords[1], pid=pid)
    elif action_type == "type":
        if value:
            ghost_log("interactions", "action", f"Typing: '{value[:40]}'")
            if coords:
                click(coords[0], coords[1], pid=pid)
                time.sleep(0.2)
            type_text(value, pid=pid)
    elif action_type == "key_press":
        if key:
            mod_str = "+".join(modifiers) + "+" if modifiers else ""
            ghost_log("interactions", "action", f"Key: {mod_str}{key}")
            key_press(key, modifiers, pid=pid)
    elif action_type == "drag":
        if coords and drag_end:
            ghost_log("interactions", "action", f"Drag ({coords[0]},{coords[1]}) -> ({drag_end[0]},{drag_end[1]})")
            drag(coords[0], coords[1], drag_end[0], drag_end[1], pid=pid)
    elif action_type == "scroll":
        if coords:
            ghost_log("interactions", "action", f"Scroll {scroll_dir or 'down'} at ({coords[0]}, {coords[1]})")
            scroll(coords[0], coords[1], direction=scroll_dir or "down", pid=pid)
    else:
        ghost_log("interactions", "warning", f"Unknown action type: {action_type}")
    return True


def run_discovery(pid: int, app_name: str,
                  scan_dir: str = None,
                  max_states: int = 50,
                  max_time_seconds: int = 300) -> dict:
    """
    Main entry point. Explores the app via DFS and returns the app graph.

    The returned graph matches the contract schema expected by teammates.
    """
    if scan_dir is None:
        from quest.config import SCANS_DIR
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        scan_dir = os.path.join(SCANS_DIR, f"{app_name}_{timestamp}")
    os.makedirs(os.path.join(scan_dir, "screenshots"), exist_ok=True)

    start_time = time.time()
    state_index = 0
    states = {}
    dfs_stack = []
    interaction_history = []
    visited_signatures = set()

    # --- Initial state ---
    ghost_log("mapper", "phase_start", f"Starting discovery of {app_name}",
              {"pid": pid, "max_states": max_states, "max_time": max_time_seconds})
    time.sleep(1)  # let the app settle

    # Bring app to foreground
    focus_app(pid)

    # Get app window bounds once — used to filter out-of-window elements/actions
    window_bounds = get_focused_window_bounds(pid)
    ghost_log("mapper", "info", f"Window bounds: {window_bounds}")

    ax_tree = get_ax_tree(pid)
    elements = get_interactable_elements(ax_tree)
    elements = _filter_elements_to_window(elements, window_bounds)
    sig = _elements_signature(elements)
    ss_path = _save_screenshot(scan_dir, state_index, pid)

    # Ask vision LLM for initial analysis
    vision_result = analyze_screenshot(
        ss_path, elements, app_description=app_name, explored_states=[]
    )

    state_name = f"state_{state_index}_{vision_result.get('state_signature', 'initial')}"
    visited_signatures.add(sig)

    # Strip internal _ax_element refs for storage
    stored_elements = []
    for e in elements:
        stored = {k: v for k, v in e.items() if k != "_ax_element"}
        stored_elements.append(stored)

    # Add vision-detected elements (skip ones with clearly invalid positions)
    for ve in vision_result.get("additional_elements", []):
        pos = ve.get("position")
        if not pos or not isinstance(pos, list) or len(pos) < 2:
            continue
        if pos[0] == 0 and pos[1] == 0:
            continue
        # Skip if position is outside the window bounds
        if window_bounds and not _is_within_bounds(pos, window_bounds):
            continue
        ve_id = f"elem_{len(stored_elements)}"
        ve_elem = {
            "id": ve_id,
            "role": "AXUnknown",
            "title": ve.get("description", ""),
            "description": ve.get("description", ""),
            "position": pos,
            "size": [30, 30],
            "actions": [ve.get("suggested_action", "click")],
            "value": None,
            "enabled": True,
            "source": "vision",
        }
        stored_elements.append(ve_elem)
        # Also add to live elements_by_id so DFS can click them by coordinate
        elements_by_id[ve_id] = ve_elem

    states[state_name] = {
        "screenshot": f"screenshots/state_{state_index}.png",
        "description": vision_result.get("screen_description", "Initial state"),
        "elements": stored_elements,
        "transitions": {},
    }

    dfs_stack.append(state_name)
    current_state = state_name
    state_index += 1

    # Build ID lookup (includes _ax_element for interaction)
    elements_by_id = {e["id"]: e for e in elements}

    ghost_log("mapper", "state_change", f"Initial state: {state_name}",
              {"state": state_name, "elements": len(elements)},
              screenshot=ss_path)

    # --- DFS loop ---
    consecutive_same_state = 0
    max_consecutive_same = 3  # reduced from 5 — backtrack faster
    # Track which elements we've already tried in each state
    tried_in_state: dict[str, set] = {state_name: set()}

    while (
        state_index < max_states
        and (time.time() - start_time) < max_time_seconds
        and dfs_stack
    ):
        elapsed = int(time.time() - start_time)
        ghost_log("mapper", "info", f"Step {state_index}",
                  {"states": len(states), "stack_depth": len(dfs_stack), "elapsed": elapsed})

        # Refresh window bounds (window may have moved/resized)
        window_bounds = get_focused_window_bounds(pid) or window_bounds

        # Always refocus the target app before doing anything — prevents
        # stray clicks landing on VS Code or other windows you're using
        focus_app(pid)
        time.sleep(0.2)

        # Build list of already-tried elements for this state
        tried_here = tried_in_state.get(current_state, set())

        # Get LLM decision
        decision = get_llm_decision(
            ax_elements=elements,
            screenshot_path=ss_path,
            explored_states=states,
            current_state=current_state,
            dfs_stack=dfs_stack,
            app_name=app_name,
            interaction_history=interaction_history,
            tried_elements=list(tried_here),
        )

        if decision is None:
            ghost_log("mapper", "warning", "LLM returned no decision, backtracking")
            _backtrack(dfs_stack)
            continue

        ghost_log("mapper", "action", f"{decision.get('action_type')} -> {decision.get('target')}",
                  {"reasoning": decision.get("reasoning", "")[:120]})

        # If LLM picked something we already tried, force backtrack
        target_id = decision.get("target")
        if target_id and target_id in tried_here:
            ghost_log("mapper", "info", f"Already tried {target_id} in this state, skipping")
            consecutive_same_state += 1
            if consecutive_same_state >= max_consecutive_same:
                ghost_log("mapper", "info", "Forcing backtrack — stuck on repeated elements")
                _backtrack(dfs_stack)
                consecutive_same_state = 0
                if dfs_stack:
                    current_state = dfs_stack[-1]
                    key_press("escape", pid=pid)
                    time.sleep(0.5)
                else:
                    break
            continue

        # Record target as tried in this state
        if target_id:
            tried_in_state.setdefault(current_state, set()).add(target_id)

        # Execute the action (blocked if coordinates land outside app window)
        # Events are sent directly to the app's PID — no focus stealing needed.
        action_ok = _execute_action(decision, elements_by_id, window_bounds, pid=pid)
        if not action_ok:
            consecutive_same_state += 1
            continue
        interaction_history.append({
            "state": current_state,
            "action": decision.get("action_type"),
            "target": target_id,
            "coordinates": decision.get("coordinates"),
        })

        # Wait for UI to settle
        time.sleep(0.8)

        # Read new state
        new_ax_tree = get_ax_tree(pid)
        new_elements = _filter_elements_to_window(get_interactable_elements(new_ax_tree), window_bounds)
        new_sig = _elements_signature(new_elements)
        new_ss_path = _save_screenshot(scan_dir, state_index, pid)

        # Extra dedup: compare screenshot file sizes as a quick similarity check.
        # If the AX signature is new but the screenshot is almost identical,
        # the AX tree likely just had a minor dynamic change (timer tick, etc.)
        try:
            old_size = os.path.getsize(ss_path)
            new_size = os.path.getsize(new_ss_path)
            size_ratio = min(old_size, new_size) / max(old_size, new_size) if max(old_size, new_size) > 0 else 1.0
            if new_sig not in visited_signatures and size_ratio > 0.95:
                ghost_log("mapper", "info",
                          f"Screenshot nearly identical (ratio={size_ratio:.3f}), treating as same state")
                visited_signatures.add(new_sig)  # mark as visited so we don't keep re-checking
        except OSError:
            size_ratio = 0.0

        if new_sig not in visited_signatures:
            # NEW STATE discovered
            consecutive_same_state = 0
            visited_signatures.add(new_sig)

            new_vision = analyze_screenshot(
                new_ss_path, new_elements,
                app_description=app_name,
                explored_states=list(states.keys()),
            )

            new_state_name = f"state_{state_index}_{new_vision.get('state_signature', 'new')}"

            new_stored = []
            for e in new_elements:
                new_stored.append({k: v for k, v in e.items() if k != "_ax_element"})

            for ve in new_vision.get("additional_elements", []):
                pos = ve.get("position")
                if not pos or not isinstance(pos, list) or len(pos) < 2:
                    continue
                if pos[0] == 0 and pos[1] == 0:
                    continue
                if window_bounds and not _is_within_bounds(pos, window_bounds):
                    continue
                ve_id = f"elem_{len(new_stored)}"
                ve_elem = {
                    "id": ve_id,
                    "role": "AXUnknown",
                    "title": ve.get("description", ""),
                    "description": ve.get("description", ""),
                    "position": pos,
                    "size": [30, 30],
                    "actions": [ve.get("suggested_action", "click")],
                    "value": None,
                    "enabled": True,
                    "source": "vision",
                }
                new_stored.append(ve_elem)

            states[new_state_name] = {
                "screenshot": f"screenshots/state_{state_index}.png",
                "description": new_vision.get("screen_description", ""),
                "elements": new_stored,
                "transitions": {},
            }

            # Record transition
            action_target = decision.get("target") or f"coord_{decision.get('coordinates')}"
            if current_state in states:
                states[current_state]["transitions"][str(action_target)] = new_state_name

            dfs_stack.append(new_state_name)
            current_state = new_state_name
            tried_in_state[new_state_name] = set()
            elements = new_elements
            elements_by_id = {e["id"]: e for e in elements}
            ss_path = new_ss_path
            state_index += 1

            ghost_log("mapper", "state_change", f"NEW STATE: {new_state_name}",
                      {"state": new_state_name, "elements": len(new_elements)},
                      screenshot=new_ss_path)

        else:
            # Same or already-visited state
            consecutive_same_state += 1
            elements = new_elements
            elements_by_id = {e["id"]: e for e in elements}
            ss_path = new_ss_path

            if consecutive_same_state >= max_consecutive_same:
                ghost_log("mapper", "info", f"No new states after {max_consecutive_same} actions, backtracking")
                _backtrack(dfs_stack)
                consecutive_same_state = 0

                if dfs_stack:
                    current_state = dfs_stack[-1]
                    # Try pressing Escape to dismiss any dialogs
                    key_press("escape", pid=pid)
                    time.sleep(0.5)
                else:
                    break

    elapsed = int(time.time() - start_time)
    ghost_log("mapper", "phase_end", f"Discovery complete: {len(states)} states in {elapsed}s",
              {"total_states": len(states), "elapsed": elapsed})

    # Count total elements
    total_elements = sum(len(s.get("elements", [])) for s in states.values())

    app_graph = {
        "app_name": app_name,
        "pid": pid,
        "timestamp": datetime.now().isoformat(),
        "total_states": len(states),
        "total_elements": total_elements,
        "states": states,
    }

    # Save graph to scan dir
    graph_path = os.path.join(scan_dir, "app_graph.json")
    with open(graph_path, "w") as f:
        json.dump(app_graph, f, indent=2)
    ghost_log("mapper", "info", f"Saved app graph to {graph_path}")

    return app_graph


def _backtrack(dfs_stack: list[str]) -> None:
    """Pop the DFS stack (backtrack to previous state)."""
    if dfs_stack:
        popped = dfs_stack.pop()
        ghost_log("mapper", "info", f"Backtracked from {popped}")
