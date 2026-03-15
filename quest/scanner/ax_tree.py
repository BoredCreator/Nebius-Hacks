"""
Accessibility tree reader for macOS applications.
Uses pyobjc to interface with macOS Accessibility APIs.

Requires:
  pip install pyobjc-framework-ApplicationServices pyobjc-framework-Cocoa
  User must enable Accessibility permissions in
  System Preferences > Privacy & Security > Accessibility
"""

from quest.dashboard.logger import ghost_log
from ApplicationServices import (
    AXUIElementCreateApplication,
    AXUIElementCopyAttributeValue,
    AXUIElementCopyAttributeNames,
    AXUIElementPerformAction,
    AXUIElementCopyActionNames,
)
import re

# AX roles considered interactable
INTERACTABLE_ROLES = {
    "AXButton",
    "AXRadioButton",
    "AXCheckBox",
    "AXPopUpButton",
    "AXComboBox",
    "AXTextField",
    "AXTextArea",
    "AXSlider",
    "AXMenuItem",
    "AXMenuButton",
    "AXMenuBarItem",
    "AXLink",
    "AXTab",
    "AXTabGroup",
    "AXIncrementor",
    "AXDisclosureTriangle",
    "AXColorWell",
    "AXToolbar",
    "AXSegmentedControl",
}


def _ax_get(element, attr):
    """Safely get an AX attribute value, returning None on failure."""
    err, value = AXUIElementCopyAttributeValue(element, attr, None)
    if err == 0:
        return value
    return None


def _ax_actions(element):
    """Get available actions for an AX element."""
    err, actions = AXUIElementCopyActionNames(element, None)
    if err == 0 and actions:
        return list(actions)
    return []


def _ax_attr_names(element):
    """Get all attribute names for an AX element."""
    err, names = AXUIElementCopyAttributeNames(element, None)
    if err == 0 and names:
        return list(names)
    return []


def _extract_position(element):
    """Extract screen position (x, y) from an AX element."""
    pos_val = _ax_get(element, "AXPosition")
    if pos_val is not None:
        try:
            m = re.search(r'x:([\d.]+)\s+y:([\d.]+)', str(pos_val))
            if m:
                return [int(float(m.group(1))), int(float(m.group(2)))]
        except Exception:
            pass
    return None


def _extract_size(element):
    """Extract size (width, height) from an AX element."""
    size_val = _ax_get(element, "AXSize")
    if size_val is not None:
        try:
            m = re.search(r'w:([\d.]+)\s+h:([\d.]+)', str(size_val))
            if m:
                return [int(float(m.group(1))), int(float(m.group(2)))]
        except Exception:
            pass
    return None


def _build_tree(element, depth=0, max_depth=15):
    """Recursively build a dict tree from an AX element."""
    if depth > max_depth:
        return None

    role = _ax_get(element, "AXRole") or "Unknown"
    title = _ax_get(element, "AXTitle")
    description = _ax_get(element, "AXDescription")
    value = _ax_get(element, "AXValue")
    enabled = _ax_get(element, "AXEnabled")
    position = _extract_position(element)
    size = _extract_size(element)
    actions = _ax_actions(element)
    role_description = _ax_get(element, "AXRoleDescription")
    subrole = _ax_get(element, "AXSubrole")

    node = {
        "role": str(role) if role else None,
        "subrole": str(subrole) if subrole else None,
        "title": str(title) if title else None,
        "description": str(description) if description else None,
        "role_description": str(role_description) if role_description else None,
        "value": str(value) if value is not None else None,
        "enabled": bool(enabled) if enabled is not None else True,
        "position": position,
        "size": size,
        "actions": actions,
        "children": [],
        "_ax_element": element,  # keep reference for performing actions
    }

    children = _ax_get(element, "AXChildren")
    if children:
        for child in children:
            child_node = _build_tree(child, depth + 1, max_depth)
            if child_node:
                node["children"].append(child_node)

    return node


def get_ax_tree(pid: int) -> dict:
    """
    Get the full accessibility tree of an app by PID.
    Returns a nested dict of all UI elements.
    """
    app_element = AXUIElementCreateApplication(pid)
    tree = _build_tree(app_element)
    if tree is None:
        return {"role": "AXApplication", "title": "Unknown", "children": []}
    return tree


def _flatten_elements(node, elements, counter):
    """Recursively flatten the tree into a list of interactable elements."""
    role = node.get("role", "")
    actions = node.get("actions", [])
    position = node.get("position")
    size = node.get("size")

    # Consider an element interactable if it has a known role or has actions (excluding containers)
    is_interactable = (
        role in INTERACTABLE_ROLES
        or (len(actions) > 0
            and role not in ("AXGroup", "AXScrollArea", "AXSplitGroup", "AXApplication", "AXWindow"))
    )

    if is_interactable and position and size:
        elem = {
            "id": f"elem_{counter[0]}",
            "role": role,
            "title": node.get("title"),
            "description": node.get("description"),
            "position": position,
            "size": size,
            "actions": actions,
            "value": node.get("value"),
            "enabled": node.get("enabled", True),
            "source": "ax_tree",
            "_ax_element": node.get("_ax_element"),
        }
        elements.append(elem)
        counter[0] += 1

    for child in node.get("children", []):
        _flatten_elements(child, elements, counter)


def get_interactable_elements(ax_tree: dict) -> list[dict]:
    """
    Flatten the tree and return only elements that can be interacted with.
    """
    elements = []
    counter = [0]
    _flatten_elements(ax_tree, elements, counter)
    return elements


def perform_ax_action(element_ref, action: str) -> bool:
    """
    Perform an accessibility action on an element.
    element_ref: the _ax_element reference from get_interactable_elements
    action: e.g. 'AXPress', 'AXConfirm', 'AXIncrement', etc.
    Returns True on success.
    """
    if element_ref is None:
        return False
    try:
        err = AXUIElementPerformAction(element_ref, action)
        return err == 0
    except Exception:
        return False
