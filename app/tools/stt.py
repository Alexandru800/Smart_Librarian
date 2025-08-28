from __future__ import annotations
from pathlib import Path
from typing import Optional
from openai import OpenAI
import io

from app.config import STT_MODEL

client = OpenAI()


def transcribe_wav(path: Path, language: str = "en") -> str:
    """
    Transcribe a local audio file using OpenAI Whisper (whisper-1).
    Returns plain text ("" if nothing).
    """
    path = Path(path)
    with path.open("rb") as f:
        resp = client.audio.transcriptions.create(
            model=STT_MODEL,
            file=f,
            language=language,
            response_format="text",
        )
    # For response_format="text", resp is a string-like; for json, use resp.text
    return str(resp or "").strip()


def transcribe_bytes(data: bytes, filename: str = "audio.wav", language: str = "en") -> str:
    """
    Transcribe from in-memory bytes. Handy for uploads.
    """
    bio = io.BytesIO(data)
    bio.name = filename  # OpenAI SDK inspects filename for format
    resp = client.audio.transcriptions.create(
        model=STT_MODEL,
        file=bio,
        language=language,
        response_format="text",
    )
    return str(resp or "").strip()