from __future__ import annotations
from pathlib import Path
from typing import Iterable
import hashlib, json
from openai import OpenAI

from app.config import TTS_MODEL, TTS_VOICE, TTS_FORMAT, AUDIO_DIR

client = OpenAI()


def _chunk_text(text: str, max_chars: int = 2500) -> list[str]:
    """Simple character-based chunking (safe for TTS)."""
    text = (text or "").strip()
    if not text:
        return []
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]


def make_tts_key(text: str, model: str = TTS_MODEL, voice: str = TTS_VOICE, fmt: str = TTS_FORMAT) -> str:
    """Generate a unique key for TTS requests based on text, model, voice, and format."""
    payload = {"t": text, "m": model, "v": voice, "f": fmt}
    h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return h[:12]


def _synthesize_chunk_bytes(text: str, *, model: str, voice: str, fmt: str) -> bytes:
    """Call OpenAI TTS for a single chunk; returns raw audio bytes."""
    # Non-streaming; simple and reliable for Streamlit
    resp = client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        response_format=fmt,
    )
    return resp.read()  # bytes


def synthesize_to_file(text: str, *, model: str | None = None, voice: str | None = None, fmt: str | None = None) -> Path:
    """
    Create (or return cached) audio file for text using selected voice/model/format.
    Returns the absolute file path.
    """
    if not text or not text.strip():
        raise ValueError("Empty text for TTS.")
    model = model or TTS_MODEL
    voice = voice or TTS_VOICE
    fmt = fmt or TTS_FORMAT

    key = make_tts_key(text, model=model, voice=voice, fmt=fmt)
    out_path = (AUDIO_DIR / f"{key}.{fmt}").resolve()
    if out_path.exists():
        return out_path

    chunks = _chunk_text(text)
    if len(chunks) == 1:
        audio_bytes = _synthesize_chunk_bytes(chunks[0], model=model, voice=voice, fmt=fmt)
    else:
        audio_bytes = b"".join(_synthesize_chunk_bytes(c, model=model, voice=voice, fmt=fmt) for c in chunks)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(audio_bytes)
    return out_path