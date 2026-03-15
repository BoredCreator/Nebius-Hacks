#!/usr/bin/env python3
"""
populate_demo.py — Quest Demo Data Generator

Creates a realistic "Pulse" app scan in quest/scans/ and streams a full
pipeline simulation (Discovery → Generation → Execution → Reporting) to the
Quest log file so the dashboard shows live, realistic data.

Usage:
    python populate_demo.py            # stream with realistic delays (~45s)
    python populate_demo.py --fast     # stream with minimal delays (~5s)
    python populate_demo.py --static   # write files only, no log streaming
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

BASE      = Path(__file__).parent
SCANS_DIR = BASE / "quest" / "scans"
LOG_DIR   = BASE / "logs"
LOG_FILE  = LOG_DIR / "appghost.log"
SCAN_NAME = "Pulse_20260315_demo"
SCAN_DIR  = SCANS_DIR / SCAN_NAME

FAST   = "--fast"   in sys.argv
STATIC = "--static" in sys.argv

DELAY_FAST   = 0.05
DELAY_NORMAL = 0.35


def delay(t=None):
    if STATIC:
        return
    time.sleep(t if t is not None else (DELAY_FAST if FAST else DELAY_NORMAL))


# ─── Logging ──────────────────────────────────────────────────────────────────

_seq = 0

def emit(source: str, level: str, message: str, data: dict = None, screenshot: str = None):
    global _seq
    _seq += 1
    event = {
        "id":        f"{source}_{int(time.time() * 1000)}_{_seq}",
        "timestamp": datetime.now().isoformat(),
        "epoch_ms":  int(time.time() * 1000),
        "source":    source,
        "level":     level,
        "message":   message,
        "data":      data or {},
        "screenshot": screenshot,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")
    return event


def section(title: str):
    print(f"\n  \033[92m{'─'*50}\033[0m")
    print(f"  \033[92m  {title}\033[0m")
    print(f"  \033[92m{'─'*50}\033[0m")


# ─── Scan Data ────────────────────────────────────────────────────────────────

APP_GRAPH = {
    "app_name": "Pulse",
    "pid": 78342,
    "timestamp": "2026-03-15T14:23:11.453821",
    "total_states": 8,
    "total_elements": 387,
    "states": {
        "state_0_login_screen": {
            "screenshot": "screenshots/state_0.png",
            "description": "Login screen with Pulse branding, email/password fields and Sign In button.",
            "elements": [
                {"id": "elem_0",  "role": "AXStaticText",      "title": "Pulse",               "description": None,               "position": [556, 290], "size": [88, 32],  "actions": [],           "value": None,              "enabled": True,  "source": "ax_tree"},
                {"id": "elem_1",  "role": "AXStaticText",      "title": None,                  "description": "Sign in to your workspace", "position": [474, 330], "size": [252, 18], "actions": [],      "value": None,              "enabled": True,  "source": "ax_tree"},
                {"id": "elem_2",  "role": "AXTextField",        "title": "Email address",       "description": None,               "position": [448, 395], "size": [304, 36], "actions": ["AXPress"], "value": "demo@pulse.app",  "enabled": True,  "source": "ax_tree"},
                {"id": "elem_3",  "role": "AXSecureTextField",  "title": "Password",            "description": None,               "position": [448, 455], "size": [304, 36], "actions": ["AXPress"], "value": "••••••••",        "enabled": True,  "source": "ax_tree"},
                {"id": "elem_4",  "role": "AXStaticText",       "title": "Forgot password?",    "description": None,               "position": [680, 498], "size": [120, 16], "actions": ["AXPress"], "value": None,              "enabled": True,  "source": "ax_tree"},
                {"id": "elem_5",  "role": "AXButton",           "title": "Sign In",             "description": None,               "position": [448, 520], "size": [304, 42], "actions": ["AXPress"], "value": None,              "enabled": True,  "source": "ax_tree"},
                {"id": "elem_6",  "role": "AXStaticText",       "title": "Demo: demo@pulse.app / demo123", "description": None,   "position": [470, 572], "size": [260, 16], "actions": [],           "value": None,              "enabled": True,  "source": "ax_tree"},
            ],
        },
        "state_1_dashboard": {
            "screenshot": "screenshots/state_1.png",
            "description": "Main dashboard with 5 stat cards, recent tasks list, and activity feed.",
            "elements": [
                {"id": "elem_10", "role": "AXButton",  "title": "⊞",         "description": "Dashboard",  "position": [16, 148], "size": [194, 38], "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_11", "role": "AXButton",  "title": "✓",         "description": "Tasks",      "position": [16, 190], "size": [194, 38], "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_12", "role": "AXButton",  "title": "⬡",         "description": "Projects",   "position": [16, 232], "size": [194, 38], "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_13", "role": "AXButton",  "title": "◎",         "description": "Team",       "position": [16, 274], "size": [194, 38], "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_14", "role": "AXButton",  "title": "⚙",         "description": "Settings",   "position": [16, 324], "size": [194, 38], "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_20", "role": "AXStaticText", "title": "12",      "description": "Total Tasks","position": [230, 200], "size": [100, 60], "actions": [],           "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_21", "role": "AXStaticText", "title": "4",       "description": "In Progress","position": [350, 200], "size": [100, 60], "actions": [],           "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_22", "role": "AXStaticText", "title": "2",       "description": "Completed",  "position": [470, 200], "size": [100, 60], "actions": [],           "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_23", "role": "AXStaticText", "title": "2",       "description": "Overdue",    "position": [590, 200], "size": [100, 60], "actions": [],           "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_24", "role": "AXStaticText", "title": "6",       "description": "Team Members","position": [710, 200], "size": [100, 60], "actions": [],          "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_30", "role": "AXButton",  "title": "+ New Task", "description": None,         "position": [855, 295], "size": [100, 28], "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_40", "role": "AXTextField", "title": "Search tasks…", "description": None,    "position": [248, 15],  "size": [264, 30], "actions": ["AXPress"], "value": "",   "enabled": True, "source": "ax_tree"},
                {"id": "elem_41", "role": "AXButton",  "title": "🔔",         "description": "Notifications","position": [1130, 13],"size": [30, 34],  "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
            ],
        },
        "state_2_tasks_view": {
            "screenshot": "screenshots/state_2.png",
            "description": "Tasks list view with filter dropdowns, task rows, checkboxes, and priority badges.",
            "elements": [
                {"id": "elem_50", "role": "AXButton",       "title": "+ New Task",  "description": None,        "position": [234, 80], "size": [100, 34], "actions": ["AXPress"],     "value": None,      "enabled": True,  "source": "ax_tree"},
                {"id": "elem_51", "role": "AXPopUpButton",  "title": "Priority",    "description": "Filter",    "position": [380, 83], "size": [110, 28], "actions": ["AXPress"],     "value": "All",     "enabled": True,  "source": "ax_tree"},
                {"id": "elem_52", "role": "AXPopUpButton",  "title": "Status",      "description": "Filter",    "position": [510, 83], "size": [120, 28], "actions": ["AXPress"],     "value": "All",     "enabled": True,  "source": "ax_tree"},
                {"id": "elem_60", "role": "AXCheckBox",     "title": "Design new landing page",    "description": "High / Mar 18",    "position": [234, 130], "size": [800, 40], "actions": ["AXPress"], "value": "0", "enabled": True, "source": "ax_tree"},
                {"id": "elem_61", "role": "AXCheckBox",     "title": "Fix login bug on mobile",    "description": "Critical / Mar 15","position": [234, 172], "size": [800, 40], "actions": ["AXPress"], "value": "0", "enabled": True, "source": "ax_tree"},
                {"id": "elem_62", "role": "AXCheckBox",     "title": "Update API documentation",   "description": "Medium / Mar 22",  "position": [234, 214], "size": [800, 40], "actions": ["AXPress"], "value": "0", "enabled": True, "source": "ax_tree"},
                {"id": "elem_63", "role": "AXCheckBox",     "title": "Set up CI/CD pipeline",      "description": "High / Mar 20",    "position": [234, 256], "size": [800, 40], "actions": ["AXPress"], "value": "0", "enabled": True, "source": "ax_tree"},
                {"id": "elem_64", "role": "AXCheckBox",     "title": "User research interviews",   "description": "Low / Mar 25",     "position": [234, 298], "size": [800, 40], "actions": ["AXPress"], "value": "0", "enabled": True, "source": "ax_tree"},
                {"id": "elem_65", "role": "AXCheckBox",     "title": "Performance optimization",   "description": "Medium / Done",    "position": [234, 340], "size": [800, 40], "actions": ["AXPress"], "value": "1", "enabled": True, "source": "ax_tree"},
                {"id": "elem_66", "role": "AXCheckBox",     "title": "Write unit tests for auth",  "description": "High / Mar 17",    "position": [234, 382], "size": [800, 40], "actions": ["AXPress"], "value": "0", "enabled": True, "source": "ax_tree"},
                {"id": "elem_70", "role": "AXScrollBar",    "title": None,          "description": "Scroll tasks", "position": [1040, 120], "size": [14, 500], "actions": ["AXScrollUpByPage","AXScrollDownByPage"], "value": None, "enabled": True, "source": "ax_tree"},
            ],
        },
        "state_3_new_task_dialog": {
            "screenshot": "screenshots/state_3.png",
            "description": "Modal dialog for creating a new task with title, description, priority, assignee, and due date fields.",
            "elements": [
                {"id": "elem_80", "role": "AXStaticText",   "title": "Create New Task", "description": None,   "position": [388, 110], "size": [304, 28], "actions": [],            "value": None,      "enabled": True,  "source": "ax_tree"},
                {"id": "elem_81", "role": "AXTextField",    "title": "Title *",         "description": None,   "position": [388, 175], "size": [304, 36], "actions": ["AXPress"],   "value": "",        "enabled": True,  "source": "ax_tree"},
                {"id": "elem_82", "role": "AXTextArea",     "title": "Description",     "description": None,   "position": [388, 245], "size": [304, 80], "actions": ["AXPress"],   "value": "",        "enabled": True,  "source": "ax_tree"},
                {"id": "elem_83", "role": "AXPopUpButton",  "title": "Priority",        "description": None,   "position": [388, 355], "size": [144, 30], "actions": ["AXPress"],   "value": "Medium",  "enabled": True,  "source": "ax_tree"},
                {"id": "elem_84", "role": "AXPopUpButton",  "title": "Assignee",        "description": None,   "position": [544, 355], "size": [148, 30], "actions": ["AXPress"],   "value": "Alex Lim","enabled": True,  "source": "ax_tree"},
                {"id": "elem_85", "role": "AXTextField",    "title": "Due Date",        "description": None,   "position": [388, 415], "size": [304, 36], "actions": ["AXPress"],   "value": "Mar 30",  "enabled": True,  "source": "ax_tree"},
                {"id": "elem_86", "role": "AXButton",       "title": "Create Task",     "description": None,   "position": [548, 475], "size": [144, 36], "actions": ["AXPress"],   "value": None,      "enabled": True,  "source": "ax_tree"},
                {"id": "elem_87", "role": "AXButton",       "title": "Cancel",          "description": None,   "position": [388, 475], "size": [80, 36],  "actions": ["AXPress"],   "value": None,      "enabled": True,  "source": "ax_tree"},
            ],
        },
        "state_4_projects_view": {
            "screenshot": "screenshots/state_4.png",
            "description": "Projects grid showing 4 project cards with progress bars, task counts, and team sizes.",
            "elements": [
                {"id": "elem_90", "role": "AXButton",    "title": "+ New Project",         "description": None,           "position": [900, 75],  "size": [110, 32], "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_91", "role": "AXButton",    "title": "Open Project →",        "description": "Website Redesign",    "position": [234, 290], "size": [440, 32], "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_92", "role": "AXButton",    "title": "Open Project →",        "description": "Mobile App v2.0",     "position": [690, 290], "size": [440, 32], "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_93", "role": "AXButton",    "title": "Open Project →",        "description": "Q2 Marketing Campaign","position": [234, 560], "size": [440, 32], "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_94", "role": "AXButton",    "title": "Open Project →",        "description": "Data Analytics Platform","position": [690, 560], "size": [440, 32], "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
            ],
        },
        "state_5_team_view": {
            "screenshot": "screenshots/state_5.png",
            "description": "Team grid with 6 member cards showing avatars, roles, status indicators, and Message buttons.",
            "elements": [
                {"id": "elem_100", "role": "AXButton",  "title": "Invite Member", "description": None,          "position": [900, 75],  "size": [120, 32], "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_101", "role": "AXButton",  "title": "Message",       "description": "Alex Lim",    "position": [264, 352], "size": [80, 28],  "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_102", "role": "AXButton",  "title": "Message",       "description": "Blake Kim",   "position": [614, 352], "size": [80, 28],  "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_103", "role": "AXButton",  "title": "Message",       "description": "Casey Jones", "position": [964, 352], "size": [80, 28],  "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_104", "role": "AXButton",  "title": "Message",       "description": "Drew Morgan", "position": [264, 600], "size": [80, 28],  "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_105", "role": "AXButton",  "title": "Message",       "description": "Emery Silva", "position": [614, 600], "size": [80, 28],  "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_106", "role": "AXButton",  "title": "Message",       "description": "Fiona Walsh", "position": [964, 600], "size": [80, 28],  "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
            ],
        },
        "state_6_settings_view": {
            "screenshot": "screenshots/state_6.png",
            "description": "Settings panel with Account info, Preferences checkboxes, Language dropdown, Save button, and Sign Out.",
            "elements": [
                {"id": "elem_110", "role": "AXButton",      "title": "Change Photo",   "description": None,      "position": [308, 210], "size": [100, 28], "actions": ["AXPress"],  "value": None,         "enabled": True,  "source": "ax_tree"},
                {"id": "elem_111", "role": "AXTextField",   "title": "Display Name",   "description": None,      "position": [248, 270], "size": [500, 36], "actions": ["AXPress"],  "value": "Sam Taylor", "enabled": True,  "source": "ax_tree"},
                {"id": "elem_112", "role": "AXTextField",   "title": "Email Address",  "description": None,      "position": [248, 330], "size": [500, 36], "actions": ["AXPress"],  "value": "demo@pulse.app", "enabled": True, "source": "ax_tree"},
                {"id": "elem_113", "role": "AXCheckBox",    "title": "Email notifications", "description": None, "position": [730, 400], "size": [20, 20],  "actions": ["AXPress"],  "value": "1",          "enabled": True,  "source": "ax_tree"},
                {"id": "elem_114", "role": "AXCheckBox",    "title": "Dark mode (beta)", "description": None,    "position": [730, 430], "size": [20, 20],  "actions": ["AXPress"],  "value": "0",          "enabled": True,  "source": "ax_tree"},
                {"id": "elem_115", "role": "AXCheckBox",    "title": "Sound effects",   "description": None,     "position": [730, 460], "size": [20, 20],  "actions": ["AXPress"],  "value": "1",          "enabled": True,  "source": "ax_tree"},
                {"id": "elem_116", "role": "AXPopUpButton", "title": "Language",        "description": None,     "position": [248, 495], "size": [180, 30], "actions": ["AXPress"],  "value": "English",    "enabled": True,  "source": "ax_tree"},
                {"id": "elem_117", "role": "AXButton",      "title": "Save Changes",    "description": None,     "position": [248, 540], "size": [130, 38], "actions": ["AXPress"],  "value": None,         "enabled": True,  "source": "ax_tree"},
                {"id": "elem_118", "role": "AXButton",      "title": "Sign Out",        "description": None,     "position": [248, 630], "size": [90, 34],  "actions": ["AXPress"],  "value": None,         "enabled": True,  "source": "ax_tree"},
            ],
        },
        "state_7_keyboard_shortcuts_dialog": {
            "screenshot": "screenshots/state_7.png",
            "description": "Informational dialog listing keyboard shortcuts.",
            "elements": [
                {"id": "elem_120", "role": "AXStaticText", "title": "Keyboard Shortcuts", "description": None, "position": [440, 300], "size": [200, 24], "actions": [], "value": None, "enabled": True, "source": "ax_tree"},
                {"id": "elem_121", "role": "AXButton",     "title": "OK",                 "description": None, "position": [520, 430], "size": [80, 30],  "actions": ["AXPress"], "value": None, "enabled": True, "source": "ax_tree"},
            ],
        },
    },
    "transitions": [
        {"from": "state_0_login_screen",   "to": "state_1_dashboard",           "via": "elem_5",   "action": "click"},
        {"from": "state_1_dashboard",      "to": "state_2_tasks_view",          "via": "elem_11",  "action": "click"},
        {"from": "state_1_dashboard",      "to": "state_3_new_task_dialog",     "via": "elem_30",  "action": "click"},
        {"from": "state_1_dashboard",      "to": "state_4_projects_view",       "via": "elem_12",  "action": "click"},
        {"from": "state_1_dashboard",      "to": "state_5_team_view",           "via": "elem_13",  "action": "click"},
        {"from": "state_1_dashboard",      "to": "state_6_settings_view",       "via": "elem_14",  "action": "click"},
        {"from": "state_2_tasks_view",     "to": "state_3_new_task_dialog",     "via": "elem_50",  "action": "click"},
        {"from": "state_3_new_task_dialog","to": "state_2_tasks_view",          "via": "elem_87",  "action": "click"},
        {"from": "state_6_settings_view",  "to": "state_7_keyboard_shortcuts_dialog", "via": "Help menu", "action": "menu"},
        {"from": "state_7_keyboard_shortcuts_dialog", "to": "state_6_settings_view", "via": "elem_121", "action": "click"},
        {"from": "state_6_settings_view",  "to": "state_0_login_screen",       "via": "elem_118", "action": "click"},
    ],
}


# ─── Test Cases ───────────────────────────────────────────────────────────────

TEST_CASES_RUSHER = [
    {
        "test_id": "test_rusher_001",
        "persona_id": "rusher",
        "persona_name": "The Rusher",
        "title": "Rapid login and task creation",
        "description": "Logs in quickly and immediately creates a task without reading labels.",
        "severity_if_fails": "high",
        "starting_state": "state_0_login_screen",
        "steps": [
            {"step_number": 1, "action": "click",    "target": "elem_2", "coordinates": None, "value": None, "expected_result": "Email field focused",  "failure_indicators": ["App unresponsive"]},
            {"step_number": 2, "action": "type",     "target": "elem_2", "coordinates": None, "value": "demo@pulse.app", "expected_result": "Email entered", "failure_indicators": []},
            {"step_number": 3, "action": "click",    "target": "elem_3", "coordinates": None, "value": None, "expected_result": "Password field focused", "failure_indicators": []},
            {"step_number": 4, "action": "type",     "target": "elem_3", "coordinates": None, "value": "demo123", "expected_result": "Password entered", "failure_indicators": []},
            {"step_number": 5, "action": "click",    "target": "elem_5", "coordinates": None, "value": None, "expected_result": "Dashboard visible",    "failure_indicators": ["Login failed", "Error dialog"]},
            {"step_number": 6, "action": "click",    "target": "elem_30","coordinates": None, "value": None, "expected_result": "New task dialog opens", "failure_indicators": ["No dialog appeared"]},
            {"step_number": 7, "action": "type",     "target": "elem_81","coordinates": None, "value": "Fix production issue NOW", "expected_result": "Title entered", "failure_indicators": []},
            {"step_number": 8, "action": "click",    "target": "elem_86","coordinates": None, "value": None, "expected_result": "Task created, dialog closed", "failure_indicators": ["Dialog persists", "Error shown"]},
        ],
        "cleanup_steps": [{"action": "key_press", "key": "escape", "modifiers": []}],
    },
    {
        "test_id": "test_rusher_002",
        "persona_id": "rusher",
        "persona_name": "The Rusher",
        "title": "Rapid filter switching on task list",
        "description": "Quickly switches priority filters multiple times.",
        "severity_if_fails": "medium",
        "starting_state": "state_2_tasks_view",
        "steps": [
            {"step_number": 1, "action": "click",    "target": "elem_51","coordinates": None, "value": None,       "expected_result": "Priority dropdown opens", "failure_indicators": []},
            {"step_number": 2, "action": "click",    "target": "elem_51","coordinates": None, "value": "Critical", "expected_result": "List shows Critical tasks only", "failure_indicators": ["All tasks still shown"]},
            {"step_number": 3, "action": "click",    "target": "elem_51","coordinates": None, "value": "High",     "expected_result": "List updates to High tasks", "failure_indicators": []},
            {"step_number": 4, "action": "click",    "target": "elem_51","coordinates": None, "value": "All",      "expected_result": "All tasks shown again", "failure_indicators": ["Filter stuck"]},
        ],
        "cleanup_steps": [],
    },
    {
        "test_id": "test_rusher_003",
        "persona_id": "rusher",
        "persona_name": "The Rusher",
        "title": "Spam-click New Task button",
        "description": "Clicks New Task multiple times rapidly to test for duplicate dialogs.",
        "severity_if_fails": "high",
        "starting_state": "state_1_dashboard",
        "steps": [
            {"step_number": 1, "action": "click",    "target": "elem_30","coordinates": None, "value": None, "expected_result": "Dialog opens",                  "failure_indicators": []},
            {"step_number": 2, "action": "click",    "target": "elem_30","coordinates": None, "value": None, "expected_result": "No second dialog (grabbed)",     "failure_indicators": ["Multiple dialogs stacked"]},
            {"step_number": 3, "action": "click",    "target": "elem_87","coordinates": None, "value": None, "expected_result": "Dialog dismissed",              "failure_indicators": []},
        ],
        "cleanup_steps": [],
    },
    {
        "test_id": "test_rusher_004",
        "persona_id": "rusher",
        "persona_name": "The Rusher",
        "title": "Navigate away during settings save",
        "description": "Clicks Save Changes then immediately navigates away.",
        "severity_if_fails": "high",
        "starting_state": "state_6_settings_view",
        "steps": [
            {"step_number": 1, "action": "click",    "target": "elem_111","coordinates": None, "value": None,           "expected_result": "Name field focused", "failure_indicators": []},
            {"step_number": 2, "action": "type",     "target": "elem_111","coordinates": None, "value": " Updated",     "expected_result": "Text appended",     "failure_indicators": []},
            {"step_number": 3, "action": "click",    "target": "elem_117","coordinates": None, "value": None,           "expected_result": "Save initiated",    "failure_indicators": []},
            {"step_number": 4, "action": "click",    "target": "elem_11", "coordinates": None, "value": None,           "expected_result": "Tasks view shown with data preserved", "failure_indicators": ["Settings lost", "Error on navigate"]},
        ],
        "cleanup_steps": [],
    },
    {
        "test_id": "test_rusher_005",
        "persona_id": "rusher",
        "persona_name": "The Rusher",
        "title": "Check all tasks then uncheck all rapidly",
        "description": "Rapidly toggles all task checkboxes.",
        "severity_if_fails": "medium",
        "starting_state": "state_2_tasks_view",
        "steps": [
            {"step_number": i + 1, "action": "click", "target": f"elem_{60+i}", "coordinates": None, "value": None,
             "expected_result": f"Task {i+1} toggled", "failure_indicators": ["Counter not updating"]}
            for i in range(5)
        ],
        "cleanup_steps": [],
    },
]

TEST_CASES_HACKER = [
    {
        "test_id": "test_hacker_001",
        "persona_id": "hacker",
        "persona_name": "The Hacker",
        "title": "SQL injection in task title",
        "description": "Attempts SQL injection via the task title field.",
        "severity_if_fails": "critical",
        "starting_state": "state_3_new_task_dialog",
        "steps": [
            {"step_number": 1, "action": "click",  "target": "elem_81","coordinates": None, "value": None,                              "expected_result": "Title field focused",    "failure_indicators": []},
            {"step_number": 2, "action": "type",   "target": "elem_81","coordinates": None, "value": "'; DROP TABLE tasks; --",          "expected_result": "Injection string accepted as text", "failure_indicators": ["App crashes", "Data wiped"]},
            {"step_number": 3, "action": "click",  "target": "elem_86","coordinates": None, "value": None,                              "expected_result": "Task saved safely",     "failure_indicators": ["Data corruption", "500 error"]},
        ],
        "cleanup_steps": [],
    },
    {
        "test_id": "test_hacker_002",
        "persona_id": "hacker",
        "persona_name": "The Hacker",
        "title": "Emoji and zalgo text in task title",
        "description": "Enters emoji and zalgo unicode to test rendering and stability.",
        "severity_if_fails": "critical",
        "starting_state": "state_3_new_task_dialog",
        "steps": [
            {"step_number": 1, "action": "click",  "target": "elem_81","coordinates": None, "value": None,                              "expected_result": "Field focused",    "failure_indicators": []},
            {"step_number": 2, "action": "type",   "target": "elem_81","coordinates": None, "value": "🔥💀🎉 T̷̡͙͘e̷̟͑̅s̶̥͊̕t̷̬͋͝ 🚀🛸",  "expected_result": "Emoji rendered, app stable", "failure_indicators": ["App freezes", "Crash", "Hang"]},
            {"step_number": 3, "action": "click",  "target": "elem_86","coordinates": None, "value": None,                              "expected_result": "Task created with emoji title", "failure_indicators": ["App unresponsive after submit"]},
        ],
        "cleanup_steps": [],
    },
    {
        "test_id": "test_hacker_003",
        "persona_id": "hacker",
        "persona_name": "The Hacker",
        "title": "XSS attempt in description field",
        "description": "Attempts script injection via the description textarea.",
        "severity_if_fails": "high",
        "starting_state": "state_3_new_task_dialog",
        "steps": [
            {"step_number": 1, "action": "click",  "target": "elem_82","coordinates": None, "value": None,                              "expected_result": "Description field focused", "failure_indicators": []},
            {"step_number": 2, "action": "type",   "target": "elem_82","coordinates": None, "value": "<script>alert('xss')</script>",    "expected_result": "String stored as literal text", "failure_indicators": ["Alert fired", "Script executed"]},
            {"step_number": 3, "action": "click",  "target": "elem_86","coordinates": None, "value": None,                              "expected_result": "Task created safely",  "failure_indicators": []},
        ],
        "cleanup_steps": [],
    },
    {
        "test_id": "test_hacker_004",
        "persona_id": "hacker",
        "persona_name": "The Hacker",
        "title": "Overflow task title field with 10000 characters",
        "description": "Pastes an extremely long string to test input length limits.",
        "severity_if_fails": "medium",
        "starting_state": "state_3_new_task_dialog",
        "steps": [
            {"step_number": 1, "action": "click",  "target": "elem_81","coordinates": None, "value": None,                              "expected_result": "Field focused", "failure_indicators": []},
            {"step_number": 2, "action": "type",   "target": "elem_81","coordinates": None, "value": "A" * 10000,                       "expected_result": "Input truncated or accepted safely", "failure_indicators": ["Memory spike", "App lag > 3s", "Crash"]},
            {"step_number": 3, "action": "click",  "target": "elem_86","coordinates": None, "value": None,                              "expected_result": "Task saved without crash", "failure_indicators": []},
        ],
        "cleanup_steps": [],
    },
]

TEST_CASES_METHODICAL = [
    {
        "test_id": "test_methodical_001",
        "persona_id": "methodical",
        "persona_name": "The Methodical Tester",
        "title": "Full task CRUD workflow",
        "description": "Creates, updates, completes, and verifies a task through the full lifecycle.",
        "severity_if_fails": "high",
        "starting_state": "state_1_dashboard",
        "steps": [
            {"step_number": 1, "action": "click",  "target": "elem_11", "coordinates": None, "value": None,        "expected_result": "Tasks view shown",     "failure_indicators": []},
            {"step_number": 2, "action": "click",  "target": "elem_50", "coordinates": None, "value": None,        "expected_result": "New task dialog opens", "failure_indicators": []},
            {"step_number": 3, "action": "type",   "target": "elem_81", "coordinates": None, "value": "Methodical Test Task", "expected_result": "Title entered", "failure_indicators": []},
            {"step_number": 4, "action": "click",  "target": "elem_83", "coordinates": None, "value": "High",      "expected_result": "Priority set to High", "failure_indicators": []},
            {"step_number": 5, "action": "click",  "target": "elem_86", "coordinates": None, "value": None,        "expected_result": "Task created, appears in list", "failure_indicators": ["Task not in list"]},
            {"step_number": 6, "action": "click",  "target": "elem_60", "coordinates": None, "value": None,        "expected_result": "Task checked/done",     "failure_indicators": ["Checkbox unresponsive"]},
            {"step_number": 7, "action": "click",  "target": "elem_52", "coordinates": None, "value": "Done",      "expected_result": "Only Done tasks shown, includes new task", "failure_indicators": ["Task not in Done filter"]},
        ],
        "cleanup_steps": [],
    },
    {
        "test_id": "test_methodical_002",
        "persona_id": "methodical",
        "persona_name": "The Methodical Tester",
        "title": "Verify all navigation items route correctly",
        "description": "Systematically clicks each nav item and verifies the correct view loads.",
        "severity_if_fails": "high",
        "starting_state": "state_1_dashboard",
        "steps": [
            {"step_number": 1, "action": "click",  "target": "elem_11", "coordinates": None, "value": None, "expected_result": "Tasks view shown",    "failure_indicators": ["Wrong view loaded"]},
            {"step_number": 2, "action": "click",  "target": "elem_12", "coordinates": None, "value": None, "expected_result": "Projects view shown", "failure_indicators": ["Wrong view loaded"]},
            {"step_number": 3, "action": "click",  "target": "elem_13", "coordinates": None, "value": None, "expected_result": "Team view shown",     "failure_indicators": ["Wrong view loaded"]},
            {"step_number": 4, "action": "click",  "target": "elem_14", "coordinates": None, "value": None, "expected_result": "Settings view shown", "failure_indicators": ["Wrong view loaded"]},
            {"step_number": 5, "action": "click",  "target": "elem_10", "coordinates": None, "value": None, "expected_result": "Dashboard shown",     "failure_indicators": ["Wrong view loaded"]},
        ],
        "cleanup_steps": [],
    },
    {
        "test_id": "test_methodical_003",
        "persona_id": "methodical",
        "persona_name": "The Methodical Tester",
        "title": "Dashboard stat card accuracy check",
        "description": "Verifies stat cards match actual task counts.",
        "severity_if_fails": "medium",
        "starting_state": "state_1_dashboard",
        "steps": [
            {"step_number": 1, "action": "click",    "target": "elem_10",  "coordinates": None, "value": None, "expected_result": "Dashboard visible", "failure_indicators": []},
            {"step_number": 2, "action": "click",    "target": "elem_11",  "coordinates": None, "value": None, "expected_result": "Tasks view: count matches dashboard",  "failure_indicators": ["Count mismatch"]},
            {"step_number": 3, "action": "click",    "target": "elem_52",  "coordinates": None, "value": "Done","expected_result": "Done count matches dashboard",         "failure_indicators": ["Count mismatch after filter"]},
            {"step_number": 4, "action": "click",    "target": "elem_10",  "coordinates": None, "value": None, "expected_result": "Dashboard refreshed with correct count","failure_indicators": ["Stale counter"]},
        ],
        "cleanup_steps": [],
    },
    {
        "test_id": "test_methodical_004",
        "persona_id": "methodical",
        "persona_name": "The Methodical Tester",
        "title": "Settings save persists across navigation",
        "description": "Modifies settings, saves, navigates away, and checks settings retained.",
        "severity_if_fails": "high",
        "starting_state": "state_6_settings_view",
        "steps": [
            {"step_number": 1, "action": "click",  "target": "elem_114", "coordinates": None, "value": None,           "expected_result": "Dark mode checkbox toggled",  "failure_indicators": []},
            {"step_number": 2, "action": "click",  "target": "elem_117", "coordinates": None, "value": None,           "expected_result": "Save dialog / confirmation",  "failure_indicators": ["No feedback on save"]},
            {"step_number": 3, "action": "click",  "target": "elem_10",  "coordinates": None, "value": None,           "expected_result": "Dashboard shown",             "failure_indicators": []},
            {"step_number": 4, "action": "click",  "target": "elem_14",  "coordinates": None, "value": None,           "expected_result": "Settings re-open with dark mode still checked", "failure_indicators": ["Setting reverted", "Checkbox unchecked"]},
        ],
        "cleanup_steps": [{"action": "click", "target": "elem_114"}, {"action": "click", "target": "elem_117"}],
    },
    {
        "test_id": "test_methodical_005",
        "persona_id": "methodical",
        "persona_name": "The Methodical Tester",
        "title": "Cancel task creation preserves list state",
        "description": "Opens new task dialog, fills form, cancels, verifies no task added.",
        "severity_if_fails": "medium",
        "starting_state": "state_2_tasks_view",
        "steps": [
            {"step_number": 1, "action": "click",  "target": "elem_50", "coordinates": None, "value": None,        "expected_result": "Dialog opens",               "failure_indicators": []},
            {"step_number": 2, "action": "type",   "target": "elem_81", "coordinates": None, "value": "Ghost Task", "expected_result": "Title filled",              "failure_indicators": []},
            {"step_number": 3, "action": "click",  "target": "elem_87", "coordinates": None, "value": None,        "expected_result": "Dialog closes, no task added","failure_indicators": ["Ghost Task appears in list"]},
        ],
        "cleanup_steps": [],
    },
    {
        "test_id": "test_methodical_006",
        "persona_id": "methodical",
        "persona_name": "The Methodical Tester",
        "title": "Project progress bar visual accuracy",
        "description": "Checks that progress bars correctly reflect percentage values.",
        "severity_if_fails": "low",
        "starting_state": "state_4_projects_view",
        "steps": [
            {"step_number": 1, "action": "click",  "target": "elem_12",  "coordinates": None, "value": None, "expected_result": "Projects view loads",           "failure_indicators": []},
            {"step_number": 2, "action": "click",  "target": "elem_91",  "coordinates": None, "value": None, "expected_result": "Website Redesign dialog/view",  "failure_indicators": ["No response to click"]},
        ],
        "cleanup_steps": [],
    },
]

# ─── Report ───────────────────────────────────────────────────────────────────

REPORT = {
    "scan_name": SCAN_NAME,
    "app_name":  "Pulse",
    "generated": "2026-03-15T15:04:44.112834",
    "summary": {
        "total_tests":  15,
        "passed":        9,
        "failed":        4,
        "errors":        2,
        "bugs_found":    5,
        "duration_secs": 248.7,
    },
    "bugs": [
        {
            "bug_id":    "BUG-001",
            "severity":  "critical",
            "title":     "App freezes when emoji + zalgo text entered in task title",
            "persona":   "hacker",
            "test_id":   "test_hacker_002",
            "step":      2,
            "description": (
                "When The Hacker persona enters a mix of emoji and zalgo unicode characters "
                "into the task title field, the application becomes unresponsive for 8–12 seconds. "
                "The main thread appears to block on text rendering. On 2 of 3 runs the app recovered; "
                "on 1 run it required force-quit."
            ),
            "reproduction_steps": [
                "Open New Task dialog",
                "Paste '🔥💀🎉 T̷̡͙͘e̷̟͑̅s̶̥͊̕t̷̬͋͝ 🚀🛸' into the Title field",
                "Click Create Task",
            ],
            "evidence": "evidence/hacker_test_hacker_002_step2.png",
            "error_type": "hang",
            "detected_at": "2026-03-15T14:51:22.341000",
        },
        {
            "bug_id":    "BUG-002",
            "severity":  "high",
            "title":     "Task counter on Dashboard not updated after toggling checkbox",
            "persona":   "methodical",
            "test_id":   "test_methodical_003",
            "step":      4,
            "description": (
                "After marking a task as done in the Tasks view and returning to Dashboard, "
                "the 'Completed' stat card still shows the old count. The counter only updates "
                "after a full navigation cycle (leave and re-enter Dashboard)."
            ),
            "reproduction_steps": [
                "Go to Tasks view",
                "Toggle any unchecked task to Done",
                "Navigate to Dashboard",
                "Observe 'Completed' counter — it is stale by 1",
            ],
            "evidence": "evidence/methodical_test_methodical_003_step4.png",
            "error_type": "state_mismatch",
            "detected_at": "2026-03-15T14:55:10.881000",
        },
        {
            "bug_id":    "BUG-003",
            "severity":  "high",
            "title":     "Settings changes silently discarded when navigating during save animation",
            "persona":   "rusher",
            "test_id":   "test_rusher_004",
            "step":      4,
            "description": (
                "Clicking 'Save Changes' and then immediately clicking a sidebar nav item "
                "(within ~200ms) causes the save to be silently cancelled. No error is shown "
                "and the user believes settings were saved, but the old values persist on "
                "next visit to Settings."
            ),
            "reproduction_steps": [
                "Go to Settings",
                "Modify Display Name",
                "Click 'Save Changes'",
                "Immediately click 'Tasks' in sidebar",
                "Return to Settings — name is reverted",
            ],
            "evidence": "evidence/rusher_test_rusher_004_step4.png",
            "error_type": "data_loss",
            "detected_at": "2026-03-15T14:47:05.209000",
        },
        {
            "bug_id":    "BUG-004",
            "severity":  "medium",
            "title":     "Priority filter dropdown resets to 'All' after task checkbox toggle",
            "persona":   "methodical",
            "test_id":   "test_methodical_001",
            "step":      6,
            "description": (
                "When a task checkbox is toggled while a priority filter is active (e.g., 'High'), "
                "the _refresh_task_list() call re-renders the view and the Combobox widget "
                "resets to 'All' because self.filter_priority is re-initialised."
            ),
            "reproduction_steps": [
                "Go to Tasks view",
                "Set Priority filter to 'High'",
                "Check any task checkbox",
                "Observe Priority filter resets to 'All'",
            ],
            "evidence": "evidence/methodical_test_methodical_001_step6.png",
            "error_type": "ui_regression",
            "detected_at": "2026-03-15T14:58:30.447000",
        },
        {
            "bug_id":    "BUG-005",
            "severity":  "low",
            "title":     "Cmd+N shortcut has no visual feedback when modal dialog is already open",
            "persona":   "rusher",
            "test_id":   "test_rusher_003",
            "step":      2,
            "description": (
                "When a modal dialog is open and the user presses Cmd+N again, "
                "nothing happens and no visual or audio feedback is provided. "
                "The user has no indication that the shortcut was ignored."
            ),
            "reproduction_steps": [
                "Click '+ New Task' to open dialog",
                "Press Cmd+N again",
                "No feedback shown",
            ],
            "evidence": None,
            "error_type": "accessibility",
            "detected_at": "2026-03-15T14:44:15.103000",
        },
    ],
    "test_results": [
        {"test_id": "test_rusher_001",      "status": "passed",  "duration_secs": 12.4, "steps_run": 8, "steps_passed": 8},
        {"test_id": "test_rusher_002",      "status": "passed",  "duration_secs":  8.1, "steps_run": 4, "steps_passed": 4},
        {"test_id": "test_rusher_003",      "status": "passed",  "duration_secs":  6.3, "steps_run": 3, "steps_passed": 3},
        {"test_id": "test_rusher_004",      "status": "failed",  "duration_secs": 14.7, "steps_run": 4, "steps_passed": 3, "failure_step": 4, "bug_ids": ["BUG-003"]},
        {"test_id": "test_rusher_005",      "status": "passed",  "duration_secs":  9.8, "steps_run": 5, "steps_passed": 5},
        {"test_id": "test_hacker_001",      "status": "passed",  "duration_secs": 11.2, "steps_run": 3, "steps_passed": 3},
        {"test_id": "test_hacker_002",      "status": "failed",  "duration_secs": 22.1, "steps_run": 3, "steps_passed": 1, "failure_step": 2, "bug_ids": ["BUG-001"]},
        {"test_id": "test_hacker_003",      "status": "passed",  "duration_secs":  9.5, "steps_run": 3, "steps_passed": 3},
        {"test_id": "test_hacker_004",      "status": "error",   "duration_secs":  5.0, "steps_run": 2, "steps_passed": 1, "failure_step": 2, "error": "Interaction timeout after 5s"},
        {"test_id": "test_methodical_001",  "status": "failed",  "duration_secs": 28.3, "steps_run": 7, "steps_passed": 5, "failure_step": 6, "bug_ids": ["BUG-004"]},
        {"test_id": "test_methodical_002",  "status": "passed",  "duration_secs": 14.9, "steps_run": 5, "steps_passed": 5},
        {"test_id": "test_methodical_003",  "status": "failed",  "duration_secs": 19.6, "steps_run": 4, "steps_passed": 3, "failure_step": 4, "bug_ids": ["BUG-002"]},
        {"test_id": "test_methodical_004",  "status": "error",   "duration_secs":  8.4, "steps_run": 3, "steps_passed": 2, "failure_step": 4, "error": "AX element elem_114 not found after navigation"},
        {"test_id": "test_methodical_005",  "status": "passed",  "duration_secs": 11.1, "steps_run": 3, "steps_passed": 3},
        {"test_id": "test_methodical_006",  "status": "passed",  "duration_secs":  7.7, "steps_run": 2, "steps_passed": 2},
    ],
}


# ─── File Creation ────────────────────────────────────────────────────────────

def create_scan_files():
    section("Creating scan directory & data files")
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    (SCAN_DIR / "screenshots").mkdir(exist_ok=True)
    (SCAN_DIR / "evidence").mkdir(exist_ok=True)
    (SCAN_DIR / "reports").mkdir(exist_ok=True)

    def write(path, data):
        path.write_text(json.dumps(data, indent=2))
        print(f"  ✓ {path.relative_to(BASE)}")

    write(SCAN_DIR / "app_graph.json",              APP_GRAPH)
    write(SCAN_DIR / "test_cases_rusher.json",      TEST_CASES_RUSHER)
    write(SCAN_DIR / "test_cases_hacker.json",      TEST_CASES_HACKER)
    write(SCAN_DIR / "test_cases_methodical.json",  TEST_CASES_METHODICAL)
    write(SCAN_DIR / "reports" / "report.json",     REPORT)


# ─── Log Streaming ────────────────────────────────────────────────────────────

def stream_logs():
    section("Streaming pipeline log events → Quest dashboard")
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Clear old log
    LOG_FILE.write_text("")
    print(f"  Log: {LOG_FILE}\n")

    # ── System boot
    emit("system", "info", "Quest v0.4.2 starting",
         {"mode": "full_pipeline", "target": "Pulse", "pid": 78342})
    delay()
    emit("system", "info", "Dashboard running at http://localhost:8000", {})
    delay()
    emit("system", "info", "Loaded 17 personas from personas.json", {"count": 17})
    delay()

    # ── Phase: Discovery
    emit("cli", "phase_start", "Starting DISCOVERY phase",
         {"phase": "discovery", "app": "Pulse", "pid": 78342})
    delay()

    emit("mapper", "info", "Launched Pulse.app (pid 78342)", {"pid": 78342})
    delay(0.6 if not FAST else 0.1)

    emit("ax_tree", "info", "AX permissions verified", {"trusted": True})
    delay()

    states = [
        ("state_0_login_screen",               "Login screen",          7),
        ("state_1_dashboard",                  "Main dashboard",        13),
        ("state_2_tasks_view",                 "Tasks list view",       11),
        ("state_3_new_task_dialog",            "New task dialog",        8),
        ("state_4_projects_view",              "Projects grid",          5),
        ("state_5_team_view",                  "Team members grid",      7),
        ("state_6_settings_view",              "Settings panel",         9),
        ("state_7_keyboard_shortcuts_dialog",  "Shortcuts dialog",       2),
    ]

    for i, (state_id, desc, elem_count) in enumerate(states):
        emit("mapper", "state_change", f"Discovered new state: {desc}",
             {"state_id": state_id, "state_index": i, "elements_found": elem_count,
              "total_states": i + 1, "transitions_from_here": 1 if i == 0 else 2})
        delay()

        emit("vision", "llm_call", f"Analysing screenshot for {state_id}",
             {"model": "Qwen/Qwen2.5-VL-72B-Instruct", "state": state_id,
              "prompt_tokens": 1247 + i * 33, "purpose": "state_description"})
        delay(0.5 if not FAST else 0.05)

        emit("vision", "llm_response", f"Vision: {desc}",
             {"state": state_id, "description": desc,
              "response_tokens": 88 + i * 12, "latency_ms": 1240 + i * 80})
        delay()

        emit("ax_tree", "info", f"Extracted {elem_count} interactive elements from {state_id}",
             {"state": state_id, "elements": elem_count, "roles": ["AXButton", "AXTextField",
                                                                    "AXCheckBox", "AXPopUpButton"]})
        delay(0.2 if not FAST else 0.02)

    emit("mapper", "info", "DFS traversal complete",
         {"total_states": 8, "total_elements": 387, "total_transitions": 11})
    delay()
    emit("cli", "phase_end", "DISCOVERY phase complete",
         {"phase": "discovery", "states": 8, "elements": 387,
          "duration_secs": 38.4, "screenshot_count": 8})
    delay(0.8 if not FAST else 0.1)

    # ── Phase: Generation
    emit("cli", "phase_start", "Starting GENERATION phase",
         {"phase": "generation", "personas": ["rusher", "hacker", "methodical"]})
    delay()

    persona_info = [
        ("rusher",     "The Rusher",              5, "Rapid, impatient user who skips reading labels"),
        ("hacker",     "The Hacker",              4, "Tries injections, edge cases, and exploit patterns"),
        ("methodical", "The Methodical Tester",   6, "Systematic, reads everything, verifies state"),
    ]

    for persona_id, persona_name, tc_count, persona_desc in persona_info:
        emit("generator", "info", f"Generating test cases for persona: {persona_name}",
             {"persona_id": persona_id, "persona_desc": persona_desc})
        delay()

        emit("generator", "llm_call", f"LLM: Generate {tc_count} test cases for {persona_name}",
             {"model": "meta-llama/Llama-3.3-70B-Instruct",
              "persona": persona_id, "states_provided": 8,
              "prompt_tokens": 3841 + tc_count * 120, "temperature": 0.7})
        delay(0.7 if not FAST else 0.07)

        emit("generator", "llm_response", f"Generated {tc_count} test cases for {persona_name}",
             {"persona": persona_id, "test_cases": tc_count,
              "response_tokens": 1220 + tc_count * 180, "latency_ms": 2340 + tc_count * 200})
        delay()

        emit("generator", "info", f"Saved test_cases_{persona_id}.json",
             {"file": f"test_cases_{persona_id}.json", "count": tc_count})
        delay(0.3 if not FAST else 0.03)

    emit("cli", "phase_end", "GENERATION phase complete",
         {"phase": "generation", "personas": 3, "total_test_cases": 15, "duration_secs": 18.2})
    delay(0.8 if not FAST else 0.1)

    # ── Phase: Execution
    emit("cli", "phase_start", "Starting EXECUTION phase",
         {"phase": "execution", "total_tests": 15, "app": "Pulse"})
    delay()

    emit("bug_detector", "info", "Bug detector armed",
         {"watching": ["crashes", "hangs", "memory_leaks", "DiagnosticReports"]})
    delay()

    for result in REPORT["test_results"]:
        tid    = result["test_id"]
        status = result["status"]
        dur    = result["duration_secs"]

        # Determine persona from test_id
        persona_id = tid.split("_")[1]
        personas = {"rusher": "The Rusher", "hacker": "The Hacker", "methodical": "The Methodical Tester"}
        persona_name = personas.get(persona_id, persona_id)

        emit("executor", "test_start", f"Running {tid} [{persona_name}]",
             {"test_id": tid, "persona": persona_name, "steps": result["steps_run"]})
        delay()

        for step_n in range(1, result["steps_run"] + 1):
            failed_step = result.get("failure_step")
            step_status = "pass" if (failed_step is None or step_n < failed_step) else "fail"

            emit("executor", "test_step", f"  Step {step_n}/{result['steps_run']}: {step_status}",
                 {"test_id": tid, "step": step_n, "status": step_status,
                  "action": "click" if step_n % 2 else "type"})
            delay(0.1 if not FAST else 0.02)

            if step_n % 2 == 0:
                emit("executor", "llm_call", f"  Evaluating step {step_n} result",
                     {"model": "Qwen/Qwen2.5-VL-72B-Instruct", "test_id": tid, "step": step_n,
                      "prompt_tokens": 1480 + step_n * 20, "purpose": "step_evaluation"})
                delay(0.15 if not FAST else 0.02)
                emit("executor", "llm_response", f"  Step {step_n} evaluation complete",
                     {"verdict": "pass" if step_status == "pass" else "fail",
                      "response_tokens": 64 + step_n * 4, "latency_ms": 890 + step_n * 30})
                delay(0.1 if not FAST else 0.01)

            if failed_step and step_n == failed_step:
                break

        # Emit any bugs found during this test
        bug_ids = result.get("bug_ids", [])
        for bug_id in bug_ids:
            bug = next((b for b in REPORT["bugs"] if b["bug_id"] == bug_id), None)
            if bug:
                emit("bug_detector", "bug", f"BUG DETECTED: {bug['title']}",
                     {"bug_id": bug["bug_id"], "severity": bug["severity"],
                      "test_id": tid, "step": bug["step"],
                      "error_type": bug["error_type"],
                      "description": bug["description"][:120] + "…"})
                delay(0.3 if not FAST else 0.05)

        result_emoji = {"passed": "✓", "failed": "✗", "error": "⚠"}.get(status, "?")
        emit("executor", "test_end", f"{result_emoji} {tid}: {status.upper()} ({dur}s)",
             {"test_id": tid, "status": status, "duration_secs": dur,
              "steps_passed": result["steps_passed"], "steps_run": result["steps_run"]})
        delay(0.4 if not FAST else 0.05)

    emit("cli", "phase_end", "EXECUTION phase complete",
         {"phase": "execution", "passed": 9, "failed": 4, "errors": 2,
          "bugs_found": 5, "duration_secs": 248.7})
    delay(0.8 if not FAST else 0.1)

    # ── Phase: Reporting
    emit("cli", "phase_start", "Starting REPORTING phase",
         {"phase": "reporting", "bugs": 5})
    delay()

    emit("reporter", "llm_call", "Generating executive summary",
         {"model": "meta-llama/Llama-3.3-70B-Instruct",
          "bugs_in": 5, "tests_in": 15, "prompt_tokens": 4200})
    delay(0.6 if not FAST else 0.06)

    emit("reporter", "llm_response", "Executive summary written",
         {"response_tokens": 480, "latency_ms": 1980})
    delay()

    emit("reporter", "info", "Saved reports/report.json",
         {"path": f"quest/scans/{SCAN_NAME}/reports/report.json",
          "size_bytes": 8241})
    delay()

    emit("cli", "phase_end", "REPORTING phase complete",
         {"phase": "reporting", "report": f"quest/scans/{SCAN_NAME}/reports/report.json",
          "duration_secs": 6.1})
    delay()

    emit("system", "info",
         "Pipeline complete. 5 bugs found across 15 test cases.",
         {"total_tests": 15, "passed": 9, "failed": 4, "errors": 2,
          "bugs": 5, "critical": 1, "high": 2, "medium": 1, "low": 1,
          "total_duration_secs": 311.4})

    section("Done! Open http://localhost:8000 to see the dashboard.")
    print(f"\n  Scan: {SCAN_DIR.relative_to(BASE)}")
    print(f"  Log:  {LOG_FILE.relative_to(BASE)}\n")


# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    create_scan_files()
    if not STATIC:
        stream_logs()
    else:
        print("\n  Static mode: files written, log streaming skipped.\n")
