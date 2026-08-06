import pytest

from backend.comparer import compare_words, accuracy
from backend.engine import get_engine

PAGE = get_engine().get_page(1)
LINES = [l for l in PAGE if l["text"]]
LINE_10 = LINES[1]  # ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ


def statuses(words):
    return [w["status"] for w in words]


def test_perfect_recitation_all_correct():
    res = compare_words(LINE_10["text"], LINE_10["words"])
    assert statuses(res) == ["correct"] * len(LINE_10["words"])
    assert accuracy(res) == 100.0


def test_diacritic_only_diff_still_correct():
    # whisper output often drops harakat
    res = compare_words("الحمد لله رب العالمين", LINE_10["words"])
    assert statuses(res) == ["correct"] * len(LINE_10["words"])


def test_single_wrong_word():
    res = compare_words("الحمد لله رب العالمين", LINE_10["words"])
    assert all(s == "correct" for s in statuses(res))


def test_wrong_word_detected():
    # change رَبِّ -> رَبُّ (distinct word but wrong form)
    res = compare_words("الحمد لله رب العالمين".replace("رب", "راب"), LINE_10["words"])
    assert "wrong" in statuses(res)


def test_missing_word():
    # user drops the final word الْعَٰلَمِينَ
    res = compare_words("الحمد لله رب", LINE_10["words"])
    real = [w for w in res if w["marker"] is None]
    assert real[-1]["status"] == "missing"


def test_extra_word_marks_wrong():
    # insert a non-existent word
    res = compare_words("الحمد لله شيء رب العالمين", LINE_10["words"])
    assert "wrong" in statuses(res)


def test_fuzzy_tolerates_alarahman():
    line = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"
    words = [w for w in get_engine().get_page(1)[0]["words"] if w["m"] is None]
    res = compare_words("بسم الله الرحمن الرحيم", words)
    assert statuses(res) == ["correct"] * 4


def test_verse_markers_never_counted():
    line = "إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ"
    res = compare_words(line, LINES[2]["words"])
    for w, s in zip(LINES[2]["words"], res):
        if w.get("m") is not None:
            assert s["status"] in ("correct",)  # markers tagged but not penalized


def test_repeated_word_both_occurrences_correct():
    # إِيَّاكَ repeats; difflib aligns it to the first occurrence, wrongly
    # leaving the second "missing". The right-to-left post-pass fixes it.
    line = next(l for l in LINES if l["n"] == 12)  # إِيَّاكَ نَعْبُدُ وَإِيَّاكَ...
    real_text = " ".join(w["t"] for w in line["words"] if w["m"] is None)
    res = compare_words(real_text, line["words"])
    assert statuses(res) == ["correct"] * len(line["words"])


def test_accuracy_partial():
    res = [{"status": "correct"}, {"status": "correct"}, {"status": "wrong"}, {"status": "missing"}]
    assert accuracy(res) == 50.0
