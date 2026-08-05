"""Orchestrates: transcribe -> normalize -> track line -> compare words."""

import json
import threading

from . import asr, comparer, config, tracker

_LOCK = threading.Lock()


class Engine:
    def __init__(self, pages_path=config.PAGES_PATH):
        with open(pages_path, encoding="utf-8") as f:
            self._data = json.load(f)
        self.pages = self._data["pages"]
        self.meta = self._data["meta"]
        self._page = None
        self._page_no = None
        self._last_line = None
        self._session = threading.local()

    # ---- page access ----
    def get_page(self, page_no: int) -> dict:
        key = str(page_no)
        if key not in self.pages:
            raise KeyError(f"page {page_no} not found")
        return self.pages[key]

    def page_info(self, page_no: int) -> dict:
        lines = []
        for line in self.get_page(page_no):
            words = [dict(w, idx=i) for i, w in enumerate(line["words"])]
            lines.append({**line, "words": words})
        return {
            "page": page_no,
            "total_pages": self.meta["total_pages"],
            "surahs": self.meta["surahs"],
            "lines": lines,
        }

    # ---- session state (per socket) ----
    def _state(self):
        st = getattr(self._session, "state", None)
        if st is None:
            st = {"page_no": 1, "last_line": None}
            self._session.state = st
        return st

    def set_page(self, page_no: int):
        st = self._state()
        st["page_no"] = page_no
        st["last_line"] = None
        self.get_page(page_no)  # validate
        return self.page_info(page_no)

    # ---- processing ----
    def process_audio(self, pcm_bytes: bytes, sample_rate: int = config.SAMPLE_RATE) -> dict:
        st = self._state()
        page = self.get_page(st["page_no"])
        lines = [l for l in page if l["text"]]

        prompt = None
        if st["last_line"] is not None:
            prompt = lines[st["last_line"]]["text"][:200]

        with _LOCK:
            text = asr.transcribe(pcm_bytes, sample_rate, initial_prompt=prompt)

        if not text:
            return {"text": "", "line": st["last_line"], "line_no": None,
                    "words": [], "accuracy": 100.0 if st["last_line"] is None else None}

        idx, score = tracker.find_current_line(text, lines, st["last_line"])
        if score < 0.15:
            idx = st["last_line"] or 0
        st["last_line"] = idx

        line = lines[idx]
        words = comparer.compare_words(text, line["words"])
        acc = comparer.accuracy(words)
        return {
            "text": text,
            "line": idx,
            "line_no": line["n"],
            "words": words,
            "accuracy": acc,
            "score": round(score, 3),
        }


_engine = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = Engine()
    return _engine
