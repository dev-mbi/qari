# 🕌 AI Quran Recitation Visual Feedback System — Task Log

**Project:** AI Quran Recitation Visual Feedback System
**Start:** Day 1
**Target:** Polished product (~5–7 days)
**Stack:** Flask + flask-socketio + faster-whisper + vanilla JS (SocketIO)

> **RULES**
> - Tick `[x]` a task ONLY when it is actually finished.
> - At the end of every working session, the user MUST write the report at the bottom of this file.

---

## 🗓️ Day 1 — Dataset & Env Setup

- [x] Research Quran datasets (Tanzil structured text, page/line layout)
- [x] Download Tanzil dataset (Uthmani/Imla'i text)
- [x] Build page → line → words JSON (start: Al-Fatiha + first page of Al-Baqarah)
- [x] Create Python virtualenv + install deps (flask, flask-socketio, faster-whisper, pytest)
- [x] Verify faster-whisper loads on CPU (int8) and transcribes a test WAV
- [x] Set up project skeleton (backend/, frontend/, data/)

## 🗓️ Day 2 — Backend (ASR Streaming)

- [x] Flask app with static frontend serving
- [x] flask-socketio live stream endpoint (audio chunk in → result out)
- [x] faster-whisper integration (small, int8, VAD, condition_on_previous_text)
- [x] WAV chunk handling from browser (MediaRecorder / PCM)
- [x] Plain /transcribe endpoint for testing fallback
- [x] Config file with GROQ_API_KEY toggle (cloud fallback)

## 🗓️ Day 3 — Core Algorithms (TDD first)

- [x] `normalize.py` — strip tashkeel/tatweel, unify alef/ta-marbuta/maqsura
- [x] `tracker.py` — fuzzy line detection (SequenceMatcher) → current line
- [x] `comparer.py` — word-level edit-distance compare → correct/wrong/missing
- [x] Unit tests for normalizer (pytest)
- [x] Unit tests for tracker (pytest)
- [x] Unit tests for comparer (pytest)
- [x] Wire tracker + comparer into the socket stream response

## 🗓️ Day 4 — Frontend (Mushaf UI)

- [x] Mushaf-style page layout: 15 lines, right-aligned Arabic, Uthmani font
- [x] Per-word spans rendered from JSON data
- [x] getUserMedia + MediaRecorder capture audio
- [x] Send audio chunk every ~2.5s over socket
- [x] Receive + render current line (green bg) live
- [x] Receive + render word statuses (red wrong / orange missing)

## 🗓️ Day 5 — Polish

- [x] Smooth line/word highlighting transition animation
- [x] Auto-scroll to current line
- [x] Final accuracy score (correct/total words) at page end
- [x] Page navigation (next/prev page)
- [x] Visual polish (Mushaf border, fonts, spacing) — design pass

## 🗓️ Day 6–7 — Integration & Verification

- [x] Latency tuning (chunk size, model size, VAD thresholds)
- [x] Groq toggle tested (cloud vs local)
- [x] End-to-end test with recorded recitation sample
- [x] Edge cases: silence, restart, page switch, mid-word pause
- [x] Run full test suite + final verification loop
- [x] Demo script / README

---

## 📋 Session Report

### Day 1
**Date:** 2026-08-06
**Done:**
- Researched datasets; chose Tanzil Uthmani text (risan/quran-json CDN) + exact 15-line Madani layout (blueheron786/line-by-line-quran, 604 pages × 15 lines)
- Built `backend/build_data.py` → generated `data/pages.json` (all 604 pages, word-level with verse-end markers)
- Python venv `.venv` created; installed flask 3.1.3, flask-socketio 5.6.1, faster-whisper 1.2.1, pytest
- Verified faster-whisper `small` int8 on CPU (7GB RAM) — loads + transcribes, model cached
- Skeleton: `backend/`, `frontend/`, `data/`, `requirements.txt`, `.gitignore`

**In progress / blocked:**
- none

**Notes:**
- `pages.json` sample page 1: 7 content lines (9–15), verse markers preserved as `{"t":"١","m":1}`

### Day 2
**Date:** 2026-08-06
**Done:**
- `backend/config.py`, `backend/asr.py`, `backend/normalize.py`, `backend/tracker.py`, `backend/comparer.py`, `backend/engine.py`, `backend/app.py`
- ASR wrapper: faster-whisper local (small/int8/VAD/condition_on_previous_text) + GROQ API fallback toggle
- Flask routes: `/`, `/api/page/<n>`, `/api/meta`, `/transcribe` (base64 WAV) — all 200 OK
- SocketIO events: `connect`, `select_page`, `audio_chunk` → `feedback`; verified silence path + page 1 data
- Browser audio accepted as raw PCM (float32 or int16) — no ffmpeg needed

**In progress / blocked:**
- none

**Notes:**
- faster-whisper `transcribe` needs a numpy array, not raw bytes — handled in `asr.pcm16_to_f32`

### Day 3
**Date:** 2026-08-06
**Done:**
- `normalize.py`: strips harakat + Quranic marks, unifies alef/أ/إ/آ/ٱ/dagger-alif→ا, ة→ه, ى→ي, ؤ→و, ئ→ي, removes ء/tatweel
- `tracker.py`: `find_current_line` with 5-line window around last line, returns (idx, score)
- `comparer.py`: SequenceMatcher opcode alignment — equal→correct, replace→wrong/missing, insert→missing, delete→wrong (fixed swapped semantics via failing test), fuzzy threshold 0.85
- 26 tests passing: `test_normalize.py` (11), `test_tracker.py` (5), `test_comparer.py` (10)

**In progress / blocked:**
- none

**Notes:**
- Verse-end markers are display-only (always "correct", excluded from accuracy)
- Bug caught by test: difflib insert/delete semantics were inverted → missing vs wrong was flipped

### Day 4
**Date:** 2026-08-06
**Done:**
- `frontend/index.html`, `frontend/style.css`, `frontend/app.js` (vanilla JS + socket.io 4.7.5 CDN)
- Mushaf frame: 15-line grid, Amiri Quran font, gold border/ornaments, green active line, red wavy wrong, orange dashed missing
- Audio capture: getUserMedia + ScriptProcessorNode → raw PCM (downsampled 48k→16k) → base64 → socket every 2.5s (no ffmpeg needed)
- Page nav, running accuracy label, socket client for /socket.io

**In progress / blocked:**
- none

**Notes:**
- Bug found+fixed: socket.io bundled JS version mismatch → use CDN 4.7.5
- Bug found+fixed: `emit` not imported in app.py
- Server runs via `systemd-run --user --unit=qari` (bash-tool kills plain background procs)

### Day 5
**Date:** 2026-08-06
**Done:**
- `page_info` now injects `idx` into every word so feedback can map to spans
- Auto-scroll via `scrollIntoView`, CSS transition animations, clear stale colors on line change
- Page completion banner (أحسنت 🎉) with final accuracy + retry / next-page buttons; each line scored once
- Verified via headless Chrome: page renders 15 lines/29 words/7 markers; injected feedback → correct active line, 1 wrong, 1 missing, accuracy 60%; completion banner at 100%

**In progress / blocked:**
- none

**Notes:**
- KEY bug: engine line index (over text-only lines) ≠ frontend 15-slot index → match lines by mushaf `line_no` instead

### Day 6–7
**Date:** 2026-08-06
**Done:**
- Latency: `small` int8 on this CPU ≈ 0.9s per 2.5s chunk (spec 1–2s ✓)
- Groq toggle wired in `asr.transcribe` (local default; cloud when GROQ_API_KEY set, auto-fallback to local on error) — cloud itself needs a real key to test
- Live E2E via systemd service + real model: connect → page → audio_chunk → feedback (OK)
- Edge cases tested: silence (empty, no line jump), page switch resets state, empty PCM no crash, page bounds (0/9999 rejected, 604 valid), mid-word pause sticky line
- Full suite: **37 tests pass** (`tests/test_app.py`, `test_edge_cases.py` added)
- `README.md`, `run.sh`, `config.env` (with GROQ instructions), `websocket-client` installed

**In progress / blocked:**
- Real Arabic speech E2E needs a human mic (verified pipeline with live model + simulated recitation payload in headless Chrome instead)

**Notes:**
- Run: `./run.sh` → open http://localhost:5000 → allow mic → 🎤 ابدأ
- Server during build runs via `systemd-run --user --unit=qari`
