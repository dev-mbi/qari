import pytest

from backend.tracker import find_current_line, best_line
from backend.engine import get_engine

PAGE = get_engine().get_page(1)
LINES = [l for l in PAGE if l["text"]]


def line_texts():
    return [l["text"] for l in LINES]


def test_perfect_line_match():
    target = "إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ"
    idx, score = find_current_line(target, LINES)
    assert LINES[idx]["n"] == 12  # mushaf line 12 starts with this ayah
    assert score > 0.7


def test_partial_prefix_matches_own_line():
    target = "ٱلْحَمْدُ لِلَّهِ"
    idx, _ = find_current_line(target, LINES)
    assert LINES[idx]["text"].startswith("ٱلْحَمْدُ")


def test_empty_text():
    idx, score = find_current_line("", LINES, last_line=3)
    assert idx == 3
    assert score == 0.0


def test_window_prefers_nearby_line():
    # recite line 2 text (index 1); window around last_line should pick it over far matches
    target = "ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ"
    idx, _ = find_current_line(target, LINES, last_line=0)
    assert idx == 1


def test_line_numbers_present():
    numbers = [l["n"] for l in LINES]
    assert numbers == sorted(numbers)
