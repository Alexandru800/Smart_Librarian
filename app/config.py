from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env once
load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

# OpenAI
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

# ChromaDB
CHROMADB_PATH = Path(os.getenv("CHROMADB_PATH", DATA_DIR / "chroma_store"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "books")

# Local data
BOOK_SUMMARIES_PATH = Path(
    os.getenv("BOOK_SUMMARIES_PATH", DATA_DIR / "book_summaries.json")
)

# Retriever config
RETRIEVER_TOP_K = int(os.getenv("RETRIEVER_TOP_K", "5"))  # per your choice


# Moderation
def _to_bool(s: str | None, default: bool = True) -> bool:
    if s is None:
        return default
    return s.strip().lower() in {"1", "true", "yes", "y", "on"}


MODERATION_ENABLED = _to_bool(os.getenv("MODERATION_ENABLED"), True)
MODERATION_PROVIDER = os.getenv("MODERATION_PROVIDER", "openai").lower()

# Text-to-speech
TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
TTS_VOICE = os.getenv("OPENAI_TTS_VOICE", "alloy")
TTS_FORMAT = os.getenv("OPENAI_TTS_FORMAT", "mp3")

# List for sidebar dropdown
TTS_VOICE_CHOICES = [
    v.strip()
    for v in os.getenv("OPENAI_TTS_VOICES", "alloy,verse").split(",")
    if v.strip()
]

# Where we cache the generated audio files
AUDIO_DIR = DATA_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Speech-to-text
STT_MODEL = os.getenv("OPENAI_STT_MODEL", "whisper-1")

# Where we save microphone recordings (for debugging)
MIC_DIR = DATA_DIR / "mic"
MIC_DIR.mkdir(parents=True, exist_ok=True)
