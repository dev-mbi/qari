#!/usr/bin/env bash
# Start the Qari server (faster-whisper local ASR).
# Usage: ./run.sh   (open http://localhost:5000)
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

# optional cloud key (faster demo)
if [ -f config.env ]; then
  set -a; . config.env; set +a
fi

exec .venv/bin/python -m backend.app
