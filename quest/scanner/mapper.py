"""Stub - teammate 2 will replace this with real accessibility tree discovery."""


def run_discovery(pid, app_name):
    """Stub - returns dummy app graph."""
    return {
        "app_name": app_name,
        "pid": pid,
        "timestamp": "2026-03-15T10:30:00",
        "total_states": 5,
        "total_elements": 23,
        "states": {
            "state_0_main_window": {
                "screenshot": "screenshots/state_0.png",
                "elements": [
                    {"id": "elem_0", "role": "AXButton", "title": "Play", "position": [100, 200], "size": [80, 30], "actions": ["AXPress"]},
                    {"id": "elem_1", "role": "AXTextField", "title": "Search", "position": [200, 50], "size": [300, 30], "actions": ["AXConfirm"]},
                    {"id": "elem_2", "role": "AXButton", "title": "Settings", "position": [500, 20], "size": [60, 30], "actions": ["AXPress"]},
                    {"id": "elem_3", "role": "AXMenuButton", "title": "File", "position": [10, 0], "size": [40, 20], "actions": ["AXPress"]},
                    {"id": "elem_4", "role": "AXButton", "title": "Library", "position": [50, 100], "size": [80, 30], "actions": ["AXPress"]},
                ],
                "transitions": {
                    "elem_2": "state_1_settings",
                    "elem_3": "state_2_file_menu",
                    "elem_4": "state_3_library",
                },
            },
            "state_1_settings": {
                "screenshot": "screenshots/state_1.png",
                "elements": [
                    {"id": "elem_5", "role": "AXCheckBox", "title": "Dark Mode", "position": [100, 100], "size": [20, 20], "actions": ["AXPress"]},
                    {"id": "elem_6", "role": "AXSlider", "title": "Volume", "position": [100, 150], "size": [200, 20], "actions": ["AXIncrement", "AXDecrement"]},
                    {"id": "elem_7", "role": "AXButton", "title": "Back", "position": [20, 20], "size": [60, 30], "actions": ["AXPress"]},
                    {"id": "elem_8", "role": "AXPopUpButton", "title": "Language", "position": [100, 200], "size": [150, 30], "actions": ["AXPress"]},
                ],
                "transitions": {
                    "elem_7": "state_0_main_window",
                },
            },
            "state_2_file_menu": {
                "screenshot": "screenshots/state_2.png",
                "elements": [
                    {"id": "elem_9", "role": "AXMenuItem", "title": "New Playlist", "position": [10, 25], "size": [150, 20], "actions": ["AXPress"]},
                    {"id": "elem_10", "role": "AXMenuItem", "title": "Import", "position": [10, 45], "size": [150, 20], "actions": ["AXPress"]},
                    {"id": "elem_11", "role": "AXMenuItem", "title": "Export", "position": [10, 65], "size": [150, 20], "actions": ["AXPress"]},
                ],
                "transitions": {
                    "elem_9": "state_4_new_playlist_dialog",
                },
            },
            "state_3_library": {
                "screenshot": "screenshots/state_3.png",
                "elements": [
                    {"id": "elem_12", "role": "AXTable", "title": "Song List", "position": [50, 80], "size": [500, 400], "actions": ["AXScrollDown", "AXScrollUp"]},
                    {"id": "elem_13", "role": "AXButton", "title": "Sort By", "position": [450, 50], "size": [80, 30], "actions": ["AXPress"]},
                    {"id": "elem_14", "role": "AXButton", "title": "Back", "position": [20, 20], "size": [60, 30], "actions": ["AXPress"]},
                ],
                "transitions": {
                    "elem_14": "state_0_main_window",
                },
            },
            "state_4_new_playlist_dialog": {
                "screenshot": "screenshots/state_4.png",
                "elements": [
                    {"id": "elem_15", "role": "AXTextField", "title": "Playlist Name", "position": [100, 100], "size": [250, 30], "actions": ["AXConfirm"]},
                    {"id": "elem_16", "role": "AXButton", "title": "Create", "position": [200, 160], "size": [80, 30], "actions": ["AXPress"]},
                    {"id": "elem_17", "role": "AXButton", "title": "Cancel", "position": [100, 160], "size": [80, 30], "actions": ["AXPress"]},
                ],
                "transitions": {
                    "elem_16": "state_3_library",
                    "elem_17": "state_0_main_window",
                },
            },
        },
    }
