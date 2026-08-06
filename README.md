# 🕌 Qari — AI Quran Recitation Visual Feedback System

Real-time Quran recitation trainer. Shows a real 15-line Madani Mushaf page, follows the reader,
highlights the current line **green**, marks mispronounced words **red** and skipped words **orange** —
with no interruptions, only visual feedback.

```
Mic → PCM chunks (2.5s) → faster-whisper (local, int8) → normalize → line tracker → word comparer
        → socket emit → Mushaf UI highlights + auto-scroll + accuracy score
```

## Features
- Exact **604-page, 15-line Madani Mushaf** layout (Tanzil Uthmani text)
- **Live position tracking** — current line highlighted green, auto-scrolls
- **Word-level mistake detection** — wrong (red) / missing (orange)
- **Accuracy score** + page-completion banner with final score
- **Local & private**: faster-whisper `small` int8 on CPU (~1s latency per 2.5s chunk, no GPU needed)
- Optional **Groq API** toggle for near-instant cloud transcription
- 37 pytest tests (normalizer, tracker, comparer, app, edge cases)

## Quick start
```bash
./run.sh                # first run installs deps + downloads whisper model (~500MB)
# open http://localhost:5000
```
Or manually:
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m backend.app
```

> **Browser won't connect?** If the page won't load, your browser may be forcing
> HTTPS (Firefox "HTTPS-only mode" / Chrome auto-upgrade) — the plain-HTTP server
> then fails. Two fixes:
> - Use the HTTPS port instead: **https://localhost:5001** (self-signed; click
>   "Advanced → continue"). Mic works here too.
> - Or open **http://localhost:5000** and disable HTTPS-only for localhost
>   (Firefox: turn off "HTTPS-Only Mode"; Chrome: `chrome://net-internals/#hsts`).

Allow microphone access, press 🎤 **ابدأ**, and recite the visible page.

## Configuration (`config.env`)
```bash
# Optional cloud fallback for faster transcription
GROQ_API_KEY=your_key_here      # free at console.groq.com
GROQ_MODEL=whisper-large-v3-turbo
# Optional model size: tiny / base / small / medium / large-v3
QARI_MODEL=small
# Speed/quality trade-off: 1 = greedy (fastest), 5 = beam search (better accuracy, ~2x slower)
QARI_BEAM_SIZE=1
# Condition decoding on the previous segment within a call (1 or 0)
QARI_CONDITION_ON_PREVIOUS=1
# VAD silence gap that separates segments, ms (default 500)
QARI_VAD_MIN_SILENCE=500
```

**Latency tricks built in:** silent chunks are dropped on the client (RMS gate)
and again on the server before the model — an empty 2.5s chunk now costs ~0.3ms
instead of ~0.9s of CPU. Audio is resampled to 16kHz through a low-pass FIR on
both client and server, so 48kHz mic input doesn't alias into the speech band.

## Tests
```bash
.venv/bin/python -m pytest tests/ -q
```

## Project layout
```
backend/        Flask + SocketIO server
  app.py        routes + socket events (audio_chunk → feedback)
  engine.py     orchestrates transcribe→track→compare
  asr.py        faster-whisper (+ Groq fallback)
  normalize.py  Arabic normalization (diacritics, alef/ta-marbuta/maqsura…)
  tracker.py    fuzzy line detection
  comparer.py   word-level SequenceMatcher comparison
  build_data.py rebuilds data/pages.json from raw Tanzil/layout sources
frontend/       vanilla JS Mushaf UI (no framework)
data/           pages.json (604 pages × 15 lines, word-level)
tests/          pytest suite
```

## Data sources
- Quran text: [Tanzil](https://tanzil.net) Uthmani (via `risan/quran-json`, CC-BY-SA 4.0)
- 15-line Madani layout: [`blueheron786/line-by-line-quran`](https://github.com/blueheron786/line-by-line-quran)

## How the comparison works
1. **Normalize**: strip diacritics/tatweel, unify أإآٱ→ا, ة→ه, ى→ي, dagger-alif→ا
2. **Track**: `SequenceMatcher` vs page lines, windowed around the last line
3. **Compare**: align word lists with difflib opcodes → `equal`=correct, `replace`=wrong,
   `insert`(actual not said)=missing, `delete`(extra said)=wrong; fuzzy threshold 0.85
