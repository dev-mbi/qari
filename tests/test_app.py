"""Integration test for the socket handlers + engine wiring.

Uses flask-socketio's in-process test client and monkeypatches ASR so no
model download is needed.
"""

import base64

import numpy as np
import pytest

from backend import asr
from backend.app import app, socketio
from backend.engine import get_engine


@pytest.fixture
def client():
    c = socketio.test_client(app)
    yield c
    c.disconnect()


@pytest.fixture(autouse=True)
def fake_asr(monkeypatch):
    def fake_transcribe(audio, sample_rate=16000, language="ar", initial_prompt=None):
        return "ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ"
    monkeypatch.setattr(asr, "transcribe", fake_transcribe)


def silence_pcm(seconds=1.0, sr=16000):
    return base64.b64encode(np.zeros(int(sr * seconds), dtype=np.int16).tobytes()).decode()


def test_connect_sends_page(client):
    page = client.get_received()[0]
    assert page["name"] == "page"
    assert page["args"][0]["total_pages"] == 604


def test_select_page(client):
    client.get_received()
    client.emit("select_page", {"page": 3})
    received = client.get_received()
    assert received[-1]["name"] == "page"
    assert received[-1]["args"][0]["page"] == 3


def test_audio_chunk_emits_feedback(client):
    client.get_received()
    client.emit("audio_chunk", {"pcm": silence_pcm(), "sample_rate": 16000})
    received = client.get_received()
    assert any(r["name"] == "feedback" for r in received)


def test_feedback_contains_line_and_words(client):
    client.get_received()
    client.emit("audio_chunk", {"pcm": silence_pcm(), "sample_rate": 16000})
    fb = [r for r in client.get_received() if r["name"] == "feedback"]
    assert fb
    payload = fb[0]["args"][0]
    assert payload["line"] is not None
    assert payload["words"]
    # reciting line 10 (الحمد لله رب العالمين) -> all words correct
    assert all(w["status"] == "correct" for w in payload["words"] if w["marker"] is None)
    assert payload["accuracy"] == 100.0


def test_engine_rejects_bad_page():
    eng = get_engine()
    with pytest.raises(KeyError):
        eng.set_page(9999)
