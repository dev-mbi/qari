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
    segments, _ = model.transcribe(
        audio_arr,
        language=language,
        beam_size=config.BEAM_SIZE,
        vad_filter=True,
        condition_on_previous_text=True,
        initial_prompt=initial_prompt,
    )
    return " ".join(seg.text for seg in segments).strip()


def transcribe_groq(audio: bytes, sample_rate: int = config.SAMPLE_RATE,
                    language: str = "ar", initial_prompt: str = None) -> str:
    from openai import OpenAI

    client = OpenAI(base_url="https://api.groq.com/openai/v1",
                    api_key=config.GROQ_API_KEY)
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
