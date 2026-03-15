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


# ---------- App Focus ----------

def focus_app(pid: int) -> None:
    """Bring an app to the foreground by PID, unminimizing its windows first."""
    # Unminimize via AX API
    try:
        from ApplicationServices import (
            AXUIElementCreateApplication,
            AXUIElementCopyAttributeValue,
            AXUIElementSetAttributeValue,
        )
        ax_app = AXUIElementCreateApplication(pid)
        err, windows = AXUIElementCopyAttributeValue(ax_app, "AXWindows", None)
        if not err and windows:
            for win in windows:
                err2, minimized = AXUIElementCopyAttributeValue(win, "AXMinimized", None)
                if not err2 and minimized:
                    AXUIElementSetAttributeValue(win, "AXMinimized", False)
                    time.sleep(0.2)
    except Exception:
        pass

    try:
        from AppKit import NSRunningApplication, NSApplicationActivateIgnoringOtherApps
        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
        if app:
            app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
            time.sleep(0.3)
    except Exception:
        # Fallback: use osascript
        try:
            subprocess.run(
                ["osascript", "-e", f'tell application "System Events" to set frontmost of (first process whose unix id is {pid}) to true'],
                capture_output=True, timeout=5,
            )
            time.sleep(0.3)
        except Exception:
            pass


# ---------- Screenshot ----------

def _ensure_focused(pid: int) -> None:
    """Make sure the target app is frontmost before sending events."""
    try:
        from AppKit import NSWorkspace
        frontmost = NSWorkspace.sharedWorkspace().frontmostApplication()
        if frontmost and frontmost.processIdentifier() == pid:
            return  # already focused
    except Exception:
        pass
    focus_app(pid)


def _post_event(event, pid: int = None) -> None:
    """Post a CGEvent directly to a PID (no focus stealing), or fall back to HID tap."""
    if pid is not None:
        try:
            Quartz.CGEventPostToPid(pid, event)
            return
        except (AttributeError, Exception):
            pass
    CGEventPost(kCGHIDEventTap, event)


def _find_app_window_id(pid: int) -> int | None:
    """Find the main window ID for an app by PID. Works with Electron apps."""
    try:
        # Try including off-screen windows too (handles app behind other windows)
        window_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID,
        )
        # Collect all windows for this PID
        app_windows = [
            w for w in window_list
            if w.get(Quartz.kCGWindowOwnerPID) == pid
        ]
        if not app_windows:
            return None

        # Prefer layer-0 (normal) windows, pick the largest one
        layer0 = [w for w in app_windows if w.get(Quartz.kCGWindowLayer, 999) == 0]
        candidates = layer0 if layer0 else app_windows

        # Sort by window area (largest first) — main window is usually biggest
        def _area(w):
            b = w.get(Quartz.kCGWindowBounds, {})
            return int(b.get("Width", 0)) * int(b.get("Height", 0))

        candidates.sort(key=_area, reverse=True)
        return candidates[0].get(Quartz.kCGWindowNumber)
    except Exception:
        return None


def screenshot(save_path: str, pid: int = None) -> str:
    """
    Take a screenshot of a specific app's window by PID.
    Uses CGWindowListCreateImage to capture the window's actual pixels
    even if the app is behind other windows. Falls back to screencapture -l.
    """
    import os
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    if pid is not None:
        window_id = _find_app_window_id(pid)

        if window_id is not None:
            # Method 1: CGWindowListCreateImage (captures behind other windows)
            try:
                image = Quartz.CGWindowListCreateImage(
                    Quartz.CGRectNull,
                    Quartz.kCGWindowListOptionIncludingWindow,
                    window_id,
                    Quartz.kCGWindowImageBoundsIgnoreFraming,
                )
                if image:
                    import CoreFoundation
                    url = CoreFoundation.CFURLCreateWithFileSystemPath(
                        None, save_path, CoreFoundation.kCFURLPOSIXPathStyle, False,
                    )
                    dest = Quartz.CGImageDestinationCreateWithURL(url, "public.png", 1, None)
                    if dest:
                        Quartz.CGImageDestinationAddImage(dest, image, None)
                        Quartz.CGImageDestinationFinalize(dest)
                        if os.path.exists(save_path) and os.path.getsize(save_path) > 100:
                            return save_path
            except Exception:
                pass

            # Method 2: screencapture -l (macOS native, by window ID)
            try:
                subprocess.run(
                    ["screencapture", "-l", str(window_id), "-x", save_path],
                    capture_output=True, timeout=10,
                )
                if os.path.exists(save_path) and os.path.getsize(save_path) > 100:
                    return save_path
            except Exception:
                pass

    # Final fallback: full screen (should rarely hit this)
    subprocess.run(["screencapture", "-x", save_path], capture_output=True)
    return save_path


# ---------- Mouse interactions ----------

def click(x: int, y: int, pid: int = None) -> None:
    """Click at absolute screen coordinates. Sends to pid directly if provided."""
    if pid:
        _ensure_focused(pid)
    point = Quartz.CGPoint(x, y)
    move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, point, 0)
    _post_event(move, pid)
    time.sleep(0.05)
    down = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, point, 0)
    _post_event(down, pid)
    time.sleep(0.05)
    up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, point, 0)
    _post_event(up, pid)
    time.sleep(0.1)


def double_click(x: int, y: int, pid: int = None) -> None:
    """Double click at coordinates."""
    if pid:
        _ensure_focused(pid)
    point = Quartz.CGPoint(x, y)
    move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, point, 0)
    _post_event(move, pid)
    time.sleep(0.05)
    down1 = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, point, 0)
    Quartz.CGEventSetIntegerValueField(down1, Quartz.kCGMouseEventClickState, 1)
    _post_event(down1, pid)
    up1 = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, point, 0)
    Quartz.CGEventSetIntegerValueField(up1, Quartz.kCGMouseEventClickState, 1)
    _post_event(up1, pid)
    time.sleep(0.02)
    down2 = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, point, 0)
    Quartz.CGEventSetIntegerValueField(down2, Quartz.kCGMouseEventClickState, 2)
    _post_event(down2, pid)
    up2 = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, point, 0)
    Quartz.CGEventSetIntegerValueField(up2, Quartz.kCGMouseEventClickState, 2)
    _post_event(up2, pid)
    time.sleep(0.1)


def right_click(x: int, y: int, pid: int = None) -> None:
    """Right click at coordinates."""
    if pid:
        _ensure_focused(pid)
    point = Quartz.CGPoint(x, y)
    move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, point, 0)
    _post_event(move, pid)
    time.sleep(0.05)
    down = CGEventCreateMouseEvent(None, kCGEventRightMouseDown, point, 0)
    _post_event(down, pid)
    time.sleep(0.05)
    up = CGEventCreateMouseEvent(None, kCGEventRightMouseUp, point, 0)
    _post_event(up, pid)
    time.sleep(0.1)


def drag(start_x: int, start_y: int, end_x: int, end_y: int,
         duration: float = 0.5, pid: int = None) -> None:
    """Click and drag from start to end coordinates."""
    if pid:
        _ensure_focused(pid)
    start = Quartz.CGPoint(start_x, start_y)
    end = Quartz.CGPoint(end_x, end_y)
    steps = max(int(duration / 0.02), 10)

    move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, start, 0)
    _post_event(move, pid)
    time.sleep(0.05)

    down = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, start, 0)
    _post_event(down, pid)
    time.sleep(0.05)

    for i in range(1, steps + 1):
        t = i / steps
        cx = start_x + (end_x - start_x) * t
        cy = start_y + (end_y - start_y) * t
        pt = Quartz.CGPoint(cx, cy)
        drag_evt = CGEventCreateMouseEvent(None, kCGEventLeftMouseDragged, pt, 0)
        _post_event(drag_evt, pid)
        time.sleep(duration / steps)

    up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, end, 0)
    _post_event(up, pid)
    time.sleep(0.1)


def scroll(x: int, y: int, direction: str = "down", amount: int = 3, pid: int = None) -> None:
    """Scroll at position. direction: 'up', 'down', 'left', 'right'."""
    if pid:
        _ensure_focused(pid)
    point = Quartz.CGPoint(x, y)
    move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, point, 0)
    _post_event(move, pid)
    time.sleep(0.05)

    if direction in ("up", "down"):
        dy = amount if direction == "up" else -amount
        evt = CGEventCreateScrollWheelEvent(None, kCGScrollEventUnitLine, 1, dy)
    else:
        dx = amount if direction == "right" else -amount
        evt = CGEventCreateScrollWheelEvent(None, kCGScrollEventUnitLine, 2, 0, dx)

    _post_event(evt, pid)
    time.sleep(0.1)


# ---------- Keyboard interactions ----------

def type_text(text: str, delay_per_char: float = 0.02, pid: int = None) -> None:
    """Type text character by character using CGEvents."""
    if pid:
        _ensure_focused(pid)
    for ch in text:
        keycode = _keycode(ch)
        needs_shift = ch.isupper() or ch in '~!@#$%^&*()_+{}|:"<>?'

        down = CGEventCreateKeyboardEvent(None, keycode, True)
        up = CGEventCreateKeyboardEvent(None, keycode, False)

        if needs_shift:
            CGEventSetFlags(down, kCGEventFlagMaskShift)
            CGEventSetFlags(up, kCGEventFlagMaskShift)

        _post_event(down, pid)
        _post_event(up, pid)
        time.sleep(delay_per_char)


def key_press(key: str, modifiers: list[str] = None, pid: int = None) -> None:
    """
    Press a key with optional modifiers.
    key: 'return', 'tab', 'escape', 'space', 'delete', 'a', 'b', etc.
    modifiers: ['cmd', 'shift', 'alt', 'ctrl']
    """
    if pid:
        _ensure_focused(pid)
    keycode = _keycode(key)
    mask = _modifier_mask(modifiers)

    down = CGEventCreateKeyboardEvent(None, keycode, True)
    up = CGEventCreateKeyboardEvent(None, keycode, False)

    if mask:
        CGEventSetFlags(down, mask)
        CGEventSetFlags(up, mask)

    _post_event(down, pid)
    time.sleep(0.05)
    _post_event(up, pid)
    time.sleep(0.1)


# ---------- Utility ----------

def get_mouse_position() -> tuple[int, int]:
    """Get current mouse position."""
    event = Quartz.CGEventCreate(None)
    point = Quartz.CGEventGetLocation(event)
    return int(point.x), int(point.y)


def get_focused_window_bounds(pid: int) -> dict | None:
    """Get the bounds of the main window for the given PID.
    Returns {"x": int, "y": int, "width": int, "height": int} or None.
    Includes off-screen/minimized windows so this works even when the app is hidden.
    """
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListExcludeDesktopElements,
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
