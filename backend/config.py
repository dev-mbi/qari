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
# Greedy (1) = fast; 5 = higher quality. Trade ~2x latency for accuracy.
BEAM_SIZE = int(os.environ.get("QARI_BEAM_SIZE", "1"))
# Condition decoding on the model's own previous segment output within a call.
CONDITION_ON_PREVIOUS = os.environ.get("QARI_CONDITION_ON_PREVIOUS", "1") == "1"
# VAD: min gap (ms) that separates speech into segments (500 = default).
VAD_MIN_SILENCE_MS = int(os.environ.get("QARI_VAD_MIN_SILENCE", "500"))
# Audio energy gate: chunks with RMS below this are treated as silence and
# never reach the ASR model (saves ~0.9s of CPU per empty chunk).
SILENCE_RMS_THRESHOLD = 0.004

# cloud fallback (optional, used only if GROQ_API_KEY is set)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "whisper-large-v3-turbo")

PAGES_PATH = DATA_DIR / "pages.json"
