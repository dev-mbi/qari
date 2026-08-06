"""Word-level mistake detection (position-aware + fuzzy).

Strategy:
  - normalize user transcription words and actual (line) words
  - align the two word lists with difflib.SequenceMatcher opcodes
  - 'equal'       -> correct
  - 'replace'     -> wrong (actual word was spoken incorrectly)
  - 'delete'      -> missing (word never spoken)
  - 'insert'      -> wrong (extra word spoken; attach to next actual word)
"""

from difflib import SequenceMatcher

from . import normalize


def _fuzzy_equal(a: str, b: str) -> bool:
    """True if words match after normalization (handles small ASR noise)."""
    na, nb = normalize.normalize(a), normalize.normalize(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if abs(len(na) - len(nb)) <= 1:
        return SequenceMatcher(None, na, nb).ratio() >= 0.85
    return False


def compare_words(user_text: str, actual_words: list[dict]) -> list[dict]:
    """Return one status per word in `actual_words`:
    {"word":..., "marker":..., "status": "correct"|"wrong"|"missing", "idx": i}
    Verse-end markers (word["m"] set) are display-only and always "correct".
    """
    user_words = [
        w for w in (normalize.remove_small(x) for x in normalize.normalize(user_text).split()) if w
    ]

    real = [(i, w) for i, w in enumerate(actual_words) if w.get("m") is None]
    actual = [normalize.remove_small(w["t"]) for _, w in real]

    status_map = {i: "missing" for i, _ in real}

    sm = SequenceMatcher(None, user_words, actual, autojunk=False)
    unmatched_user = []  # user words not consumed by an equal/replace block
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for off in range(j2 - j1):
                status_map[real[j1 + off][0]] = "correct"
        elif tag == "replace":
            n_user, n_actual = i2 - i1, j2 - j1
            for off in range(n_actual):
                ui = i1 + off
                if off < n_user and _fuzzy_equal(user_words[ui], actual[j1 + off]):
                    status_map[real[j1 + off][0]] = "correct"
                elif off < n_user:
                    status_map[real[j1 + off][0]] = "wrong"
                else:
                    status_map[real[j1 + off][0]] = "missing"
            # leftover user words from this block become candidates for repeats
            for off in range(max(0, n_user - n_actual)):
                unmatched_user.append(user_words[i1 + n_actual + off])
        elif tag == "delete":
            # user words with no actual counterpart -> candidates for repeats
            unmatched_user.extend(user_words[i1:i2])
        elif tag == "insert":
            # actual words with no user counterpart -> user skipped them
            for off in range(j2 - j1):
                status_map[real[j1 + off][0]] = "missing"

    # Repeated words: difflib aligns a repeat to its FIRST occurrence, leaving
    # the later identical word "missing" even though the reader said it. Do a
    # right-to-left pass so leftover user words match the LATER missing word.
    if unmatched_user:
        missing_idx = [i for i, st in status_map.items() if st == "missing"]
        for i in reversed(missing_idx):
            if not unmatched_user:
                break
            w = actual[i]
            for u in range(len(unmatched_user) - 1, -1, -1):
                if _fuzzy_equal(unmatched_user[u], w):
                    status_map[i] = "correct"
                    del unmatched_user[u]
                    break

    # extra user words still unaccounted for -> mark the last real word as wrong
    pending = len(unmatched_user)
    if pending > 0 and real:
        for i in range(len(real) - 1, -1, -1):
            if status_map[real[i][0]] != "missing":
                status_map[real[i][0]] = "wrong"
                pending -= 1
                if pending <= 0:
                    break

    result = []
    for i, w in enumerate(actual_words):
        if w.get("m") is not None:
            result.append({"word": w["t"], "marker": w["m"], "status": "correct", "idx": i})
        else:
            result.append({"word": w["t"], "marker": None, "status": status_map[i], "idx": i})
    return result


def accuracy(results: list[dict]) -> float:
    if not results:
        return 0.0
    return round(sum(1 for r in results if r["status"] == "correct") / len(results) * 100, 1)
