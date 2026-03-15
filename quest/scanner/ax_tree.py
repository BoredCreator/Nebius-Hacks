"""Stub accessibility tree — teammate 2 will replace with real AX API implementation."""


def get_ax_tree(pid: int) -> dict:
    """Stub: return a minimal AX tree."""
    return {"role": "AXApplication", "title": "StubApp", "children": []}


def get_interactable_elements(ax_tree: dict) -> list[dict]:
    """Stub: return empty element list."""
    return []
