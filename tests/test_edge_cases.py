"""Edge cases: silence, session reset, page bounds, engine robustness."""

import base64

import numpy as np
import pytest

from backend import asr
from backend.app import app, socketio
from backend.engine import Engine, get_engine


@pytest.fixture
def client():
    c = socketio.test_client(app)
    yield c
    c.disconnect()


@pytest.fixture(autouse=True)
def fake_asr(monkeypatch):
    def fake_transcribe(audio, sample_rate=16000, language="ar", initial_prompt=None, fmt="i16"):
        return "ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ"
    monkeypatch.setattr(asr, "transcribe", fake_transcribe)


def pcm(seconds, sr=16000):
    return base64.b64encode(np.zeros(int(sr * seconds), dtype=np.int16).tobytes()).decode()


def test_engine_silence_returns_empty(monkeypatch):
    monkeypatch.setattr(asr, "transcribe", lambda *a, **k: "")
    eng = Engine()
    eng.set_page(1)
    r = eng.process_audio(np.zeros(1600, dtype=np.int16).tobytes(), 16000)
    assert r["text"] == ""
    assert r["line"] is None


def test_engine_set_page_resets_line():
    eng = Engine()
    eng.set_page(1)
    eng.process_audio(np.zeros(16000, dtype=np.int16).tobytes(), 16000)
    eng.set_page(2)  # switching page resets tracking state
    assert eng._state()["last_line"] is None


def test_engine_empty_pcm_does_not_crash():
    eng = Engine()
    eng.set_page(1)
    r = eng.process_audio(b"", 16000)
    assert r is not None


def test_page_bounds():
    eng = get_engine()
    with pytest.raises(KeyError):
        eng.set_page(0)
    with pytest.raises(KeyError):
        eng.set_page(9999)
    eng.set_page(604)  # last page is valid


def test_mid_word_pause_keeps_session():
    """Repeated chunks keep last_line sticky so tracking doesn't jump around."""
    eng = Engine()
    eng.set_page(1)
    eng.process_audio(np.zeros(16000, dtype=np.int16).tobytes(), 16000)
    first = eng._state()["last_line"]
    eng.process_audio(np.zeros(16000, dtype=np.int16).tobytes(), 16000)
    assert eng._state()["last_line"] == first


def test_engine_low_confidence_stays_on_line(monkeypatch):
    from backend import tracker

    def low(*a, **k):
        return 0, 0.05

    monkeypatch.setattr(tracker, "find_current_line", low)
    eng = Engine()
    eng.set_page(1)
    eng._state()["last_line"] = 2
    r = eng.process_audio(np.zeros(16000, dtype=np.int16).tobytes(), 16000)
    assert eng._state()["last_line"] == 2
    assert r["line_no"] == [l for l in eng.get_page(1) if l["text"]][2]["n"]


def test_engine_first_chunk_low_confidence_no_jump(monkeypatch):
    """No line yet + low confidence must NOT jump to the first line."""
    from backend import tracker

    def low(*a, **k):
        return 0, 0.05

    monkeypatch.setattr(tracker, "find_current_line", low)
    eng = Engine()
    eng.set_page(1)
    eng._state()["last_line"] = None
    r = eng.process_audio(np.zeros(16000, dtype=np.int16).tobytes(), 16000)
    assert r["line_no"] is None
    assert eng._state()["last_line"] is None


def test_socket_select_page_bounds(client):
    client.get_received()
    client.emit("select_page", {"page": 9999})
    received = client.get_received()
    assert received and received[-1]["name"] == "error"
