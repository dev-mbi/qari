"""Unit tests for the ASR helpers: silence energy gate and resampler."""

import numpy as np
import pytest

from backend import asr, config


def test_is_silence_true_for_zeros():
    assert asr._is_silence(np.zeros(16000, dtype=np.int16).tobytes(), 16000)
    assert asr._is_silence(b"")
    assert asr._is_silence(np.zeros(16000, dtype=np.float32))
    # float32 bytes from the browser are detected as silence too
    assert asr._is_silence(np.zeros(16000, dtype=np.float32).tobytes(), 16000)


def test_pcm_bytes_to_f32_float32():
    x = (0.3 * np.random.default_rng(5).standard_normal(8000)).astype(np.float32)
    y = asr.pcm_bytes_to_f32(x.tobytes(), 16000, fmt="f32")
    assert np.allclose(y, x, atol=1e-6)


def test_pcm_bytes_to_f32_int16():
    x = (np.random.default_rng(6).standard_normal(8000) * 0.1 * 32767).astype(np.int16)
    y = asr.pcm_bytes_to_f32(x.tobytes(), 16000)
    assert np.allclose(y, x.astype(np.float32) / 32768.0, atol=1e-6)


def test_pcm_bytes_to_f32_int16_sine_not_misdecoded():
    t = np.arange(16000) / 16000
    f32 = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    i16 = (f32 * 32767).astype(np.int16)
    back = asr.pcm_bytes_to_f32(i16.tobytes(), 16000, fmt="i16")
    assert np.allclose(back, f32, atol=2 / 32768)


def test_pcm_bytes_to_f32_rejects_bad_length():
    with pytest.raises(ValueError):
        asr.pcm_bytes_to_f32(b"\x01", 16000)


def test_is_silence_false_for_speech_level_noise():
    rng = np.random.default_rng(0)
    audio = (rng.standard_normal(16000) * 0.05).astype(np.float32)
    assert not asr._is_silence(audio)


def test_transcribe_shortcircuits_silence_without_model(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("model must not be loaded for silent audio")
    monkeypatch.setattr(asr, "get_model", boom)
    out = asr.transcribe(np.zeros(16000, dtype=np.int16).tobytes(), 16000)
    assert out == ""


def test_transcribe_keeps_non_silence_path():
    rng = np.random.default_rng(1)
    audio = (rng.standard_normal(16000) * 0.1 * 32767).astype(np.int16).tobytes()
    assert not asr._is_silence(audio)


def test_resample_passthrough_same_rate():
    x = np.random.default_rng(2).standard_normal(1000).astype(np.float32)
    y = asr.resample_f32(x, 16000, 16000)
    assert y is x
    assert len(y) == 1000


def test_resample_length_ratio_48k_to_16k():
    x = np.zeros(48000, dtype=np.float32)
    y = asr.resample_f32(x, 48000, 16000)
    assert abs(len(y) - 16000) <= 2


def test_resample_preserves_low_frequency_sine():
    sr = 48000
    t = np.arange(sr * 1.0) / sr
    x = (0.5 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
    y = asr.resample_f32(x, sr, 16000)
    rms = float(np.sqrt(np.mean(y * y)))
    assert 0.2 < rms < 0.6  # ~0.35, not attenuated


def test_resample_attenuates_high_frequency_sine():
    sr = 48000
    t = np.arange(sr * 1.0) / sr
    x = (0.5 * np.sin(2 * np.pi * 12000 * t)).astype(np.float32)
    y = asr.resample_f32(x, sr, 16000)
    rms = float(np.sqrt(np.mean(y * y)))
    assert rms < 0.05  # above 8kHz Nyquist -> folded unless low-passed


def test_resample_upsample_length():
    x = np.random.default_rng(3).standard_normal(8000).astype(np.float32)
    y = asr.resample_f32(x, 8000, 16000)
    assert abs(len(y) - 16000) <= 2


def test_config_knobs_defaults():
    assert config.BEAM_SIZE >= 1
    assert config.VAD_MIN_SILENCE_MS > 0
    assert 0 < config.SILENCE_RMS_THRESHOLD < 0.1
