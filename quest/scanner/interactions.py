"""Stub interaction layer — teammate 2 will replace with real Quartz-based implementation."""

import os


def screenshot(save_path: str) -> str:
    """Stub: pretend to take screenshot."""
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "w") as f:
        f.write("placeholder_screenshot")
    return save_path


def click(x: int, y: int) -> None:
    print(f"  [INTERACTION] Click at ({x}, {y})")


def right_click(x: int, y: int) -> None:
    print(f"  [INTERACTION] Right-click at ({x}, {y})")


def double_click(x: int, y: int) -> None:
    print(f"  [INTERACTION] Double-click at ({x}, {y})")


def drag(start_x, start_y, end_x, end_y, duration=0.5) -> None:
    print(f"  [INTERACTION] Drag ({start_x},{start_y}) -> ({end_x},{end_y})")


def scroll(x, y, direction="down", amount=3) -> None:
    print(f"  [INTERACTION] Scroll {direction} at ({x},{y})")


def type_text(text: str, delay_per_char=0.02) -> None:
    print(f"  [INTERACTION] Type: '{text[:50]}...'")


def key_press(key: str, modifiers=None) -> None:
    mod_str = "+".join(modifiers) + "+" if modifiers else ""
    print(f"  [INTERACTION] Key: {mod_str}{key}")
