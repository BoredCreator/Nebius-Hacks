"""
Shared configuration for all Quest modules.
Single source of truth for API keys, paths, model names, timeouts.
Every module imports from here instead of hardcoding values.
"""

import os
from pathlib import Path

# === PATHS ===
PROJECT_ROOT = Path(__file__).parent
BASE_DIR = str(PROJECT_ROOT)  # backward compat
SCANS_DIR = os.path.join(BASE_DIR, "scans")
PERSONAS_DIR = os.path.join(BASE_DIR, "personas")
PERSONAS_FILE = os.path.join(PERSONAS_DIR, "personas.json")
APPLICATIONS_DIR = "/Applications"

# Create directories if they don't exist
os.makedirs(SCANS_DIR, exist_ok=True)

# === NEBIUS API ===
NEBIUS_API_KEY = os.environ.get("NEBIUS_API_KEY", "")
NEBIUS_API_URL = os.environ.get(
    "NEBIUS_API_URL",
    "https://api.studio.nebius.com/v1/chat/completions",
)

if not NEBIUS_API_KEY:
    print("  WARNING: NEBIUS_API_KEY not set. LLM calls will fail.")
    print("   Set it with: export NEBIUS_API_KEY=your_key_here")

# === MODEL CONFIG ===
NEBIUS_MODEL = os.environ.get("NEBIUS_MODEL", "Qwen/Qwen2.5-VL-72B-Instruct")
# Vision model (for screenshot analysis)
VISION_MODEL = os.environ.get("APPGHOST_VISION_MODEL", "Qwen/Qwen2.5-VL-72B-Instruct")
# Text-only model (for non-vision tasks)
TEXT_MODEL = os.environ.get("APPGHOST_TEXT_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
# Temperature for generation
LLM_TEMPERATURE = float(os.environ.get("APPGHOST_LLM_TEMP", "0.7"))
# Max tokens for responses
LLM_MAX_TOKENS = int(os.environ.get("APPGHOST_LLM_MAX_TOKENS", "8000"))

# === TIMEOUTS & LIMITS ===
MAX_DISCOVERY_STATES = int(os.environ.get("APPGHOST_MAX_STATES", "50"))
MAX_DISCOVERY_TIME_SECONDS = int(os.environ.get("APPGHOST_MAX_DISCOVERY_TIME", "300"))
INTERACTION_WAIT_SECONDS = float(os.environ.get("APPGHOST_INTERACTION_WAIT", "0.5"))
APP_LAUNCH_WAIT_SECONDS = float(os.environ.get("APPGHOST_APP_LAUNCH_WAIT", "3.0"))
HANG_TIMEOUT_SECONDS = float(os.environ.get("APPGHOST_HANG_TIMEOUT", "5.0"))

# === DASHBOARD ===
DASHBOARD_PORT = int(os.environ.get("APPGHOST_DASHBOARD_PORT", "8000"))
DASHBOARD_HOST = os.environ.get("APPGHOST_DASHBOARD_HOST", "0.0.0.0")


# === HELPERS ===
def get_scan_dir(app_name: str, timestamp: str = None) -> Path:
    """Generate a scan directory path with subdirectories."""
    from datetime import datetime
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = app_name.replace(" ", "_").replace("/", "_")
    scan_dir = Path(SCANS_DIR) / f"{safe_name}_{timestamp}"
    scan_dir.mkdir(parents=True, exist_ok=True)
    (scan_dir / "screenshots").mkdir(exist_ok=True)
    (scan_dir / "evidence").mkdir(exist_ok=True)
    (scan_dir / "reports").mkdir(exist_ok=True)
    return scan_dir


def validate_environment() -> dict:
    """
    Check that everything needed is available.
    Returns a dict of check_name -> (passed: bool, message: str)
    """
    checks = {}

    # API Key
    checks["nebius_api_key"] = (
        bool(NEBIUS_API_KEY),
        "NEBIUS_API_KEY is set" if NEBIUS_API_KEY else "NEBIUS_API_KEY is NOT set"
    )

    # Accessibility permissions
    try:
        from ApplicationServices import AXIsProcessTrusted
        trusted = AXIsProcessTrusted()
        checks["accessibility_permissions"] = (
            trusted,
            "Accessibility permissions granted" if trusted
            else "Accessibility permissions NOT granted. Go to System Settings > Privacy > Accessibility"
        )
    except ImportError:
        checks["accessibility_permissions"] = (
            False,
            "pyobjc not installed. Run: pip install pyobjc-framework-ApplicationServices"
        )

    # Python packages
    required_packages = [
        ("ApplicationServices", "pyobjc-framework-ApplicationServices"),
        ("Quartz", "pyobjc-framework-Quartz"),
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn[standard]"),
        ("requests", "requests"),
    ]
    for pkg, install_name in required_packages:
        try:
            __import__(pkg)
            checks[f"package_{pkg}"] = (True, f"{pkg} installed")
        except ImportError:
            checks[f"package_{pkg}"] = (False, f"{pkg} NOT installed. Run: pip install {install_name}")

    # Directories & files
    checks["scans_dir"] = (os.path.isdir(SCANS_DIR), f"Scans directory: {SCANS_DIR}")
    checks["personas_file"] = (
        os.path.isfile(PERSONAS_FILE),
        f"Personas file: {PERSONAS_FILE}" if os.path.isfile(PERSONAS_FILE)
        else f"Personas file NOT found at {PERSONAS_FILE}"
    )

    return checks
