"""App configuration."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"

# faster-whisper
MODEL_SIZE = os.environ.get("QARI_MODEL", "small")
MODEL_DEVICE = "cpu"
MODEL_COMPUTE = "int8"

# streaming
SAMPLE_RATE = 16000
BEAM_SIZE = 1

# cloud fallback (optional, used only if GROQ_API_KEY is set)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "whisper-large-v3-turbo")

PAGES_PATH = DATA_DIR / "pages.json"
