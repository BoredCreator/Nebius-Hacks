"""
Dashboard backend. Serves the web UI and provides:
- REST API for querying logs, scan data, stats
- WebSocket for real-time log streaming
- Static file serving for the frontend

Run with: uvicorn quest.dashboard.server:app --reload --port 8000
Or call: start_dashboard() from the CLI
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
import asyncio
import json
import os
import glob as globmod
from pathlib import Path

from quest.dashboard.logger import (
    get_recent_logs, get_stats, LOG_BUFFER, EVENT_LISTENERS, ghost_log
)
from quest import config

app = FastAPI(title="Quest Dashboard")

# Serve static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ============ PAGES ============

@app.get("/")
async def index():
    """Serve the main dashboard page."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# ============ REST API ============

@app.get("/api/logs")
async def api_logs(n: int = 200, source: str = None, level: str = None):
    """Get recent log events with optional filtering."""
    logs = get_recent_logs(n, source, level)
    return {"logs": logs, "total": len(logs)}


@app.get("/api/stats")
async def api_stats():
    """Get aggregate dashboard stats."""
    return get_stats()


@app.get("/api/scans")
async def api_scans():
    """List all scans in the scans/ directory."""
    scans_dir = config.SCANS_DIR
    if not os.path.exists(scans_dir):
        return {"scans": []}

    scans = []
    for scan_folder in sorted(os.listdir(scans_dir)):
        scan_path = os.path.join(scans_dir, scan_folder)
        if not os.path.isdir(scan_path):
            continue

        scan_info = {
            "name": scan_folder,
            "path": scan_path,
            "has_app_graph": os.path.exists(os.path.join(scan_path, "app_graph.json")),
            "has_screenshots": os.path.exists(os.path.join(scan_path, "screenshots")),
            "test_case_files": globmod.glob(os.path.join(scan_path, "test_cases_*.json")),
            "has_report": os.path.exists(os.path.join(scan_path, "reports", "report.json")),
        }

        # Load app graph summary if exists
        graph_path = os.path.join(scan_path, "app_graph.json")
        if os.path.exists(graph_path):
            try:
                with open(graph_path) as f:
                    graph = json.load(f)
                    scan_info["app_name"] = graph.get("app_name", "Unknown")
                    scan_info["total_states"] = graph.get("total_states", 0)
                    scan_info["total_elements"] = graph.get("total_elements", 0)
            except (json.JSONDecodeError, OSError):
                pass

        scans.append(scan_info)

    return {"scans": scans}


@app.get("/api/scans/{scan_name}/graph")
async def api_scan_graph(scan_name: str):
    """Get the app graph for a specific scan."""
    graph_path = os.path.join(config.SCANS_DIR, scan_name, "app_graph.json")
    if not os.path.exists(graph_path):
        return JSONResponse({"error": "App graph not found"}, status_code=404)
    with open(graph_path) as f:
        return json.load(f)


@app.get("/api/scans/{scan_name}/test_cases")
async def api_test_cases(scan_name: str, persona: str = None):
    """Get test cases for a scan, optionally filtered by persona."""
    scan_path = os.path.join(config.SCANS_DIR, scan_name)
    test_cases = {}

    for tc_file in globmod.glob(os.path.join(scan_path, "test_cases_*.json")):
        persona_id = os.path.basename(tc_file).replace("test_cases_", "").replace(".json", "")
        if persona and persona != persona_id:
            continue
        with open(tc_file) as f:
            test_cases[persona_id] = json.load(f)

    # Also check for the unified test_cases.json
    unified_path = os.path.join(scan_path, "test_cases.json")
    if os.path.exists(unified_path):
        with open(unified_path) as f:
            test_cases["all"] = json.load(f)

    return {"test_cases": test_cases}


@app.get("/api/scans/{scan_name}/report")
async def api_report(scan_name: str):
    """Get the execution report for a scan."""
    report_path = os.path.join(config.SCANS_DIR, scan_name, "reports", "report.json")
    if not os.path.exists(report_path):
        return JSONResponse({"error": "Report not found"}, status_code=404)
    with open(report_path) as f:
        return json.load(f)


@app.get("/api/scans/{scan_name}/screenshots/{filename}")
async def api_screenshot(scan_name: str, filename: str):
    """Serve a screenshot image."""
    img_path = os.path.join(config.SCANS_DIR, scan_name, "screenshots", filename)
    if not os.path.exists(img_path):
        # Check evidence folder too
        for root, dirs, files in os.walk(os.path.join(config.SCANS_DIR, scan_name)):
            if filename in files:
                img_path = os.path.join(root, filename)
                break

    if os.path.exists(img_path):
        return FileResponse(img_path)
    return JSONResponse({"error": "Screenshot not found"}, status_code=404)


@app.get("/api/llm_calls")
async def api_llm_calls():
    """Get all LLM call logs with prompts and responses."""
    llm_logs = get_recent_logs(500, level="llm_call") + get_recent_logs(500, level="llm_response")
    llm_logs.sort(key=lambda x: x["epoch_ms"])
    return {"llm_calls": llm_logs}


@app.get("/api/bugs")
async def api_bugs():
    """Get all discovered bugs across all scans."""
    bug_logs = get_recent_logs(500, level="bug")
    return {"bugs": bug_logs}


@app.get("/api/pipeline_status")
async def api_pipeline_status():
    """Determine current pipeline status from logs."""
    logs = list(LOG_BUFFER)

    phases = {
        "discovery": {"status": "idle", "started": None, "ended": None, "details": {}},
        "generation": {"status": "idle", "started": None, "ended": None, "details": {}},
        "execution": {"status": "idle", "started": None, "ended": None, "details": {}},
        "reporting": {"status": "idle", "started": None, "ended": None, "details": {}},
    }

    for log in logs:
        if log["level"] == "phase_start":
            phase = log["data"].get("phase")
            if phase in phases:
                phases[phase]["status"] = "running"
                phases[phase]["started"] = log["timestamp"]
        elif log["level"] == "phase_end":
            phase = log["data"].get("phase")
            if phase in phases:
                phases[phase]["status"] = "complete"
                phases[phase]["ended"] = log["timestamp"]

    test_starts = [l for l in logs if l["level"] == "test_start"]
    test_ends = [l for l in logs if l["level"] == "test_end"]
    phases["execution"]["details"] = {
        "tests_started": len(test_starts),
        "tests_completed": len(test_ends),
    }

    state_changes = [l for l in logs if l["level"] == "state_change" and l["source"] == "mapper"]
    phases["discovery"]["details"] = {
        "states_discovered": len(state_changes),
    }

    return {"phases": phases}


# ============ WEBSOCKET FOR REAL-TIME LOGS ============

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for real-time log streaming."""
    await websocket.accept()

    queue = asyncio.Queue()

    def on_event(event):
        try:
            queue.put_nowait(event)
        except Exception:
            pass

    EVENT_LISTENERS.append(on_event)

    try:
        # Send recent history first
        for log in get_recent_logs(50):
            await websocket.send_json(log)

        # Then stream new events
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        EVENT_LISTENERS.remove(on_event)
    except Exception:
        if on_event in EVENT_LISTENERS:
            EVENT_LISTENERS.remove(on_event)


def start_dashboard(port: int = 8000):
    """Start the dashboard server. Called from CLI."""
    import uvicorn
    ghost_log("system", "info", f"Starting dashboard on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
