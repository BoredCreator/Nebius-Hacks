import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCANS_DIR = os.path.join(BASE_DIR, "scans")
PERSONAS_FILE = os.path.join(BASE_DIR, "personas", "personas.json")
APPLICATIONS_DIR = "/Applications"

# Nebius AI Studio
NEBIUS_API_KEY = os.environ.get("NEBIUS_API_KEY", "")
NEBIUS_API_URL = os.environ.get(
    "NEBIUS_API_URL",
    "https://api.studio.nebius.com/v1/chat/completions",
)
NEBIUS_MODEL = os.environ.get("NEBIUS_MODEL", "Qwen/Qwen2.5-VL-72B-Instruct")
