"""
Low-level macOS interaction layer using Quartz CGEvents.
Handles all input types including those outside the accessibility tree.

Requires:
  pip install pyobjc-framework-Quartz
"""

import subprocess
import time
from quest.dashboard.logger import ghost_log

import Quartz
from Quartz import (
    CGEventCreateMouseEvent,
    CGEventPost,
    CGEventCreateKeyboardEvent,
    CGEventSetFlags,
    CGEventCreateScrollWheelEvent,
    kCGEventMouseMoved,
    kCGEventLeftMouseDown,
    kCGEventLeftMouseUp,
    kCGEventLeftMouseDragged,
    kCGEventRightMouseDown,
    kCGEventRightMouseUp,
    kCGHIDEventTap,
    kCGScrollEventUnitLine,
    kCGEventFlagMaskCommand,
    kCGEventFlagMaskShift,
    kCGEventFlagMaskAlternate,
    kCGEventFlagMaskControl,
)

# ---------- Key code lookup ----------

_KEY_CODES = {
    "a": 0, "b": 11, "c": 8, "d": 2, "e": 14, "f": 3, "g": 5, "h": 4,
    "i": 34, "j": 38, "k": 40, "l": 37, "m": 46, "n": 45, "o": 31, "p": 35,
    "q": 12, "r": 15, "s": 1, "t": 17, "u": 32, "v": 9, "w": 13, "x": 7,
    "y": 16, "z": 6,
    "0": 29, "1": 18, "2": 19, "3": 20, "4": 21, "5": 23, "6": 22, "7": 26,
    "8": 28, "9": 25,
    "return": 36, "enter": 36, "tab": 48, "space": 49, "delete": 51,
    "backspace": 51, "escape": 53, "esc": 53,
    "up": 126, "down": 125, "left": 123, "right": 124,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97,
    "f7": 98, "f8": 100, "f9": 101, "f10": 109, "f11": 103, "f12": 111,
    "-": 27, "=": 24, "[": 33, "]": 30, "\\": 42, ";": 41, "'": 39,
    ",": 43, ".": 47, "/": 44, "`": 50,
    "home": 115, "end": 119, "pageup": 116, "pagedown": 121,
    "forwarddelete": 117,
}

_MODIFIER_FLAGS = {
    "cmd": kCGEventFlagMaskCommand,
    "command": kCGEventFlagMaskCommand,
    "shift": kCGEventFlagMaskShift,
    "alt": kCGEventFlagMaskAlternate,
    "option": kCGEventFlagMaskAlternate,
    "ctrl": kCGEventFlagMaskControl,
    "control": kCGEventFlagMaskControl,
}


def _keycode(key: str) -> int:
    return _KEY_CODES.get(key.lower(), 0)


def _modifier_mask(modifiers: list[str] | None) -> int:
    if not modifiers:
        return 0
    mask = 0
    for m in modifiers:
        mask |= _MODIFIER_FLAGS.get(m.lower(), 0)
    return mask


# ---------- Screenshot ----------

def screenshot(save_path: str, pid: int = None) -> str:
    """
    Take a screenshot. If pid is given, capture only that app's windows.
    Falls back to full-screen capture via screencapture CLI.
    """
    import os
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    if pid is not None:
        # Try to capture just the app's windows
        try:
            window_list = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
                Quartz.kCGNullWindowID,
            )
            app_windows = [
                w for w in window_list
                if w.get(Quartz.kCGWindowOwnerPID) == pid
                and w.get(Quartz.kCGWindowLayer, 999) == 0
            ]
            if app_windows:
                bounds = app_windows[0].get(Quartz.kCGWindowBounds, {})
                x = int(bounds.get("X", 0))
                y = int(bounds.get("Y", 0))
                w = int(bounds.get("Width", 800))
                h = int(bounds.get("Height", 600))
                subprocess.run(
                    ["screencapture", "-R", f"{x},{y},{w},{h}", "-x", save_path],
                    check=True,
                    capture_output=True,
                )
                return save_path
        except Exception:
            pass

    # Fallback: full screen capture
    subprocess.run(["screencapture", "-x", save_path], capture_output=True)
    return save_path


# ---------- Mouse interactions ----------

def click(x: int, y: int) -> None:
    """Click at absolute screen coordinates."""
    point = Quartz.CGPoint(x, y)
    # Move mouse first
    move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, point, 0)
    CGEventPost(kCGHIDEventTap, move)
    time.sleep(0.05)
    # Mouse down + up
    down = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, point, 0)
    CGEventPost(kCGHIDEventTap, down)
    time.sleep(0.05)
    up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, point, 0)
    CGEventPost(kCGHIDEventTap, up)
    time.sleep(0.1)


def double_click(x: int, y: int) -> None:
    """Double click at coordinates."""
    point = Quartz.CGPoint(x, y)
    move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, point, 0)
    CGEventPost(kCGHIDEventTap, move)
    time.sleep(0.05)
    # First click
    down1 = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, point, 0)
    Quartz.CGEventSetIntegerValueField(down1, Quartz.kCGMouseEventClickState, 1)
    CGEventPost(kCGHIDEventTap, down1)
    up1 = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, point, 0)
    Quartz.CGEventSetIntegerValueField(up1, Quartz.kCGMouseEventClickState, 1)
    CGEventPost(kCGHIDEventTap, up1)
    time.sleep(0.02)
    # Second click
    down2 = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, point, 0)
    Quartz.CGEventSetIntegerValueField(down2, Quartz.kCGMouseEventClickState, 2)
    CGEventPost(kCGHIDEventTap, down2)
    up2 = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, point, 0)
    Quartz.CGEventSetIntegerValueField(up2, Quartz.kCGMouseEventClickState, 2)
    CGEventPost(kCGHIDEventTap, up2)
    time.sleep(0.1)


def right_click(x: int, y: int) -> None:
    """Right click at coordinates."""
    point = Quartz.CGPoint(x, y)
    move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, point, 0)
    CGEventPost(kCGHIDEventTap, move)
    time.sleep(0.05)
    down = CGEventCreateMouseEvent(None, kCGEventRightMouseDown, point, 0)
    CGEventPost(kCGHIDEventTap, down)
    time.sleep(0.05)
    up = CGEventCreateMouseEvent(None, kCGEventRightMouseUp, point, 0)
    CGEventPost(kCGHIDEventTap, up)
    time.sleep(0.1)


def drag(start_x: int, start_y: int, end_x: int, end_y: int,
         duration: float = 0.5) -> None:
    """Click and drag from start to end coordinates."""
    start = Quartz.CGPoint(start_x, start_y)
    end = Quartz.CGPoint(end_x, end_y)
    steps = max(int(duration / 0.02), 10)

    # Move to start
    move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, start, 0)
    CGEventPost(kCGHIDEventTap, move)
    time.sleep(0.05)

    # Press down
    down = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, start, 0)
    CGEventPost(kCGHIDEventTap, down)
    time.sleep(0.05)

    # Drag incrementally
    for i in range(1, steps + 1):
        t = i / steps
        cx = start_x + (end_x - start_x) * t
        cy = start_y + (end_y - start_y) * t
        pt = Quartz.CGPoint(cx, cy)
        drag_evt = CGEventCreateMouseEvent(None, kCGEventLeftMouseDragged, pt, 0)
        CGEventPost(kCGHIDEventTap, drag_evt)
        time.sleep(duration / steps)

    # Release
    up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, end, 0)
    CGEventPost(kCGHIDEventTap, up)
    time.sleep(0.1)


def scroll(x: int, y: int, direction: str = "down", amount: int = 3) -> None:
    """Scroll at position. direction: 'up', 'down', 'left', 'right'."""
    # Move mouse to position first
    point = Quartz.CGPoint(x, y)
    move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, point, 0)
    CGEventPost(kCGHIDEventTap, move)
    time.sleep(0.05)

    if direction in ("up", "down"):
        dy = amount if direction == "up" else -amount
        evt = CGEventCreateScrollWheelEvent(None, kCGScrollEventUnitLine, 1, dy)
    else:
        dx = amount if direction == "right" else -amount
        evt = CGEventCreateScrollWheelEvent(None, kCGScrollEventUnitLine, 2, 0, dx)

    CGEventPost(kCGHIDEventTap, evt)
    time.sleep(0.1)


# ---------- Keyboard interactions ----------

def type_text(text: str, delay_per_char: float = 0.02) -> None:
    """Type text character by character using CGEvents."""
    for ch in text:
        keycode = _keycode(ch)
        needs_shift = ch.isupper() or ch in '~!@#$%^&*()_+{}|:"<>?'

        down = CGEventCreateKeyboardEvent(None, keycode, True)
        up = CGEventCreateKeyboardEvent(None, keycode, False)

        if needs_shift:
            CGEventSetFlags(down, kCGEventFlagMaskShift)
            CGEventSetFlags(up, kCGEventFlagMaskShift)

        CGEventPost(kCGHIDEventTap, down)
        CGEventPost(kCGHIDEventTap, up)
        time.sleep(delay_per_char)


def key_press(key: str, modifiers: list[str] = None) -> None:
    """
    Press a key with optional modifiers.
    key: 'return', 'tab', 'escape', 'space', 'delete', 'a', 'b', etc.
    modifiers: ['cmd', 'shift', 'alt', 'ctrl']
    """
    keycode = _keycode(key)
    mask = _modifier_mask(modifiers)

    down = CGEventCreateKeyboardEvent(None, keycode, True)
    up = CGEventCreateKeyboardEvent(None, keycode, False)

    if mask:
        CGEventSetFlags(down, mask)
        CGEventSetFlags(up, mask)

    CGEventPost(kCGHIDEventTap, down)
    time.sleep(0.05)
    CGEventPost(kCGHIDEventTap, up)
    time.sleep(0.1)


# ---------- Utility ----------

def get_mouse_position() -> tuple[int, int]:
    """Get current mouse position."""
    event = Quartz.CGEventCreate(None)
    point = Quartz.CGEventGetLocation(event)
    return int(point.x), int(point.y)


def get_focused_window_bounds(pid: int) -> dict | None:
    """Get the bounds of the focused window for the given PID.
    Returns {"x": int, "y": int, "width": int, "height": int} or None.
    """
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    )
    for w in window_list:
        if w.get(Quartz.kCGWindowOwnerPID) == pid and w.get(Quartz.kCGWindowLayer, 999) == 0:
            bounds = w.get(Quartz.kCGWindowBounds, {})
            return {
                "x": int(bounds.get("X", 0)),
                "y": int(bounds.get("Y", 0)),
                "width": int(bounds.get("Width", 800)),
                "height": int(bounds.get("Height", 600)),
            }
    return None
