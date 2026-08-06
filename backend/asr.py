"""Speech recognition wrapper.

Default: faster-whisper (local, CPU, int8).
Fallback: Groq Whisper API if GROQ_API_KEY is set (config.USE_GROQ).
"""

import io
import wave
import base64

import numpy as np

from . import config

_model = None

_SILENCE_THRESHOLD = getattr(config, "SILENCE_RMS_THRESHOLD", 0.004)


def _is_silence(audio: bytes | np.ndarray, sample_rate: int = config.SAMPLE_RATE) -> bool:
    """True if the chunk has no meaningful speech energy (RMS below threshold).

    Works on 16-bit PCM bytes or a float32 numpy array. Short chunks are still
    judged on their actual RMS so brief sounds are never gated away.
    """
    if isinstance(audio, np.ndarray):
        x = audio
    else:
        if not audio:
            return True
        x = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
    if x.size == 0:
        return True
    rms = float(np.sqrt(np.mean(x * x)))
    return rms < _SILENCE_THRESHOLD


def resample_f32(samples: np.ndarray, in_rate: int, out_rate: int = config.SAMPLE_RATE) -> np.ndarray:
    """Resample a float32 signal with a proper anti-aliasing low-pass.

    Naive point-decimation folds high-frequency energy back into the speech
    band; this applies a Hamming-windowed sinc low-pass before decimation.
    """
    samples = np.asarray(samples, dtype=np.float32)
    if in_rate == out_rate or samples.size == 0:
        return samples
    ratio = in_rate / out_rate
    if ratio < 1.0:
        # upsample: linear interpolation is fine (no aliasing when upsampling)
        n_out = int(samples.size / ratio)
        x = np.linspace(0, samples.size - 1, n_out)
        return np.interp(x, np.arange(samples.size), samples).astype(np.float32)
    # decimate: low-pass at 0.45 * out_rate before picking samples
    fc = 0.45 / ratio  # cutoff normalized to the input rate
    ntaps = max(9, (int(8 * ratio) | 1))
    n = np.arange(ntaps) - (ntaps - 1) / 2.0
    h = np.sinc(2 * fc * n) * 2 * fc
    h *= np.hamming(ntaps)
    h /= h.sum()
    full = np.convolve(samples, h.astype(np.float32))
    center = (ntaps - 1) / 2.0
    n_out = int((samples.size - 1) / ratio) + 1
    pos = np.clip((center + np.arange(n_out) * ratio).astype(int), 0, full.size - 1)
    return full[pos]


def get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel(
            config.MODEL_SIZE, device=config.MODEL_DEVICE, compute_type=config.MODEL_COMPUTE
        )
    return _model


def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = config.SAMPLE_RATE) -> bytes:
    """Wrap raw PCM bytes (16-bit mono) into a WAV container (needed by decoders)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm_bytes)
    return buf.getvalue()


def float32_to_pcm16(pcm_bytes: bytes) -> bytes:
    """Convert raw Float32 (little-endian) audio to 16-bit PCM mono."""
    samples = np.frombuffer(pcm_bytes, dtype=np.float32)
    samples = np.clip(samples, -1.0, 1.0)
    return (samples * 32767).astype(np.int16).tobytes()


def pcm16_to_f32(pcm_bytes: bytes) -> np.ndarray:
    """16-bit PCM bytes -> float32 array in [-1, 1]."""
    return np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0


def transcribe_local(audio: bytes, sample_rate: int = config.SAMPLE_RATE,
                     language: str = "ar", initial_prompt: str = None) -> str:
    model = get_model()
    audio_arr = pcm16_to_f32(audio) if isinstance(audio, bytes) else audio
    if sample_rate != config.SAMPLE_RATE:
        audio_arr = resample_f32(audio_arr, sample_rate, config.SAMPLE_RATE)
    segments, _ = model.transcribe(
        audio_arr,
        language=language,
        beam_size=config.BEAM_SIZE,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": config.VAD_MIN_SILENCE_MS},
        condition_on_previous_text=config.CONDITION_ON_PREVIOUS,
        without_timestamps=True,
        initial_prompt=initial_prompt,
    )
    return " ".join(seg.text for seg in segments).strip()


def transcribe_groq(audio: bytes, sample_rate: int = config.SAMPLE_RATE,
                    language: str = "ar", initial_prompt: str = None) -> str:
    from openai import OpenAI

    client = OpenAI(base_url="https://api.groq.com/openai/v1",
                    api_key=config.GROQ_API_KEY)
    if isinstance(audio, np.ndarray):
        audio = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
    wav = pcm_to_wav(audio, sample_rate)
    result = client.audio.transcriptions.create(
        model=config.GROQ_MODEL,
        file=("chunk.wav", wav, "audio/wav"),
        language=language,
        prompt=initial_prompt,
    )
    return (result.text or "").strip()


def transcribe(audio: bytes, sample_rate: int = config.SAMPLE_RATE,
               language: str = "ar", initial_prompt: str = None) -> str:
    if _is_silence(audio, sample_rate):
        return ""
    if config.GROQ_API_KEY:
        try:
            return transcribe_groq(audio, sample_rate, language, initial_prompt)
        except Exception as e:  # fall back to local on any cloud error
            print(f"[asr] groq failed ({e}), using local")
    return transcribe_local(audio, sample_rate, language, initial_prompt)


def transcribe_b64(b64: str, sample_rate: int = config.SAMPLE_RATE,
                   language: str = "ar") -> str:
    """Transcribe a base64 WAV/raw-PCM payload (for the /transcribe endpoint)."""
    raw = base64.b64decode(b64)
    return transcribe(raw, sample_rate, language)
