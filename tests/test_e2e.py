"""
End-to-end tests for the Quest pipeline.
These tests require macOS accessibility permissions and a running GUI.
They are marked with @pytest.mark.e2e and skipped in CI.
"""

import json
import os
import shutil
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Skip all e2e tests if not on macOS or if explicitly skipped
pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="e2e tests require macOS",
)


def _has_accessibility():
    try:
        from ApplicationServices import AXIsProcessTrusted
        return AXIsProcessTrusted()
    except ImportError:
        return False


@pytest.fixture
def calculator():
    """Launch Calculator, yield its PID, then kill it."""
    from quest.app_manager import launch_app, get_app_pid, kill_app
    pid = launch_app("Calculator")
    time.sleep(2)
    actual_pid = get_app_pid("Calculator")
    yield actual_pid or pid
    try:
        kill_app(actual_pid or pid)
    except Exception:
        pass


@pytest.mark.skipif(not _has_accessibility(), reason="No accessibility permissions")
class TestE2ECalculator:

    def test_ax_tree_reads_elements(self, calculator):
        from quest.scanner.ax_tree import get_ax_tree, get_interactable_elements
        tree = get_ax_tree(calculator)
        assert tree is not None
        elements = get_interactable_elements(tree)
        assert len(elements) > 0
        # Calculator should have buttons
        roles = {e["role"] for e in elements}
        assert "AXButton" in roles or "AXGroup" in roles

    def test_screenshot_captures_image(self, calculator):
        from quest.scanner.interactions import screenshot
        import tempfile
        path = os.path.join(tempfile.gettempdir(), "e2e_calc_ss.png")
        screenshot(path, pid=calculator)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 1000
        os.remove(path)

    def test_element_has_valid_schema(self, calculator):
        from quest.scanner.ax_tree import get_ax_tree, get_interactable_elements
        tree = get_ax_tree(calculator)
        elements = get_interactable_elements(tree)
        required = {"id", "role", "position", "size", "actions"}
        for elem in elements[:5]:
            missing = required - set(elem.keys())
            assert not missing, f"Element missing: {missing}"
            assert isinstance(elem["position"], list)
            assert len(elem["position"]) == 2
            assert isinstance(elem["size"], list)
            assert len(elem["size"]) == 2

    def test_discovery_produces_valid_graph(self, calculator):
        from quest.scanner.mapper import run_discovery
        from quest.config import get_scan_dir
        scan_dir = str(get_scan_dir("Calculator", "e2e_test"))
        graph = run_discovery(calculator, "Calculator",
                              scan_dir=scan_dir, max_states=3, max_time_seconds=30)
        assert isinstance(graph, dict)
        assert "app_name" in graph
        assert "states" in graph
        assert len(graph["states"]) > 0

        # Verify graph is JSON-serializable
        json.dumps(graph, default=str)

        shutil.rmtree(scan_dir, ignore_errors=True)
