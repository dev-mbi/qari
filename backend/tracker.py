"""Position detection: find which Mushaf line the user is reading."""

from difflib import SequenceMatcher

from . import normalize

WINDOW = 5  # only re-score lines within this window of the current line


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def find_current_line(user_text: str, page_lines: list[dict], last_line: int | None = None) -> tuple[int, float]:
    """Return (line_index, score) of the best matching line.

    page_lines: list of {"n": line_no, "text": ..., "words": [...]}.
    Scores candidate lines around `last_line` (if given) then the whole page.
    """
    user_norm = normalize.normalize(user_text)
    if not user_norm:
        return last_line or 0, 0.0

    def score_for(idx):
        line_norm = normalize.normalize(page_lines[idx]["text"])
        return _similarity(user_norm, line_norm)

    # When we know the current line, only score candidates within a window.
    # Scanning the whole page lets a repeated word on a far-away line win and
    # yank the reader back to an earlier line.
    if last_line is not None:
        start = max(0, last_line - WINDOW)
        end = min(len(page_lines), last_line + WINDOW + 1)
        candidates = list(range(start, end))
        if not candidates:
            return last_line, 0.0
    else:
        candidates = list(range(len(page_lines)))

    best_idx, best_score = last_line, 0.0
    for idx in candidates:
        s = score_for(idx)
        if s > best_score:
            best_score, best_idx = s, idx
    return best_idx, best_score


def best_line(user_text: str, page_lines: list[dict], last_line: int | None = None) -> int:
    idx, _ = find_current_line(user_text, page_lines, last_line)
    return idx
