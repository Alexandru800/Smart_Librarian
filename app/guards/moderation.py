from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any
from openai import OpenAI

from app.config import MODERATION_ENABLED, MODERATION_PROVIDER


@dataclass
class ModerationResult:
    allowed: bool
    flagged: bool
    provider: str
    categories: list[str]
    error: Optional[str] = None

# Small local fallback (expand as you like)
_BLOCK_RE = re.compile(
    r"\b("
    r"fuck|shit|bitch|asshole|idiot|moron|"        # EN basics
    r"pula|dracu|fut|jigodie|nesimtit|prost"       # RO basics (mild+)
    r")\b",
    flags=re.IGNORECASE,
)


def _local_moderate(text: str) -> ModerationResult:
    if _BLOCK_RE.search(text or ""):
        return ModerationResult(allowed=False, flagged=True, provider="local", categories=["blocklist"])
    return ModerationResult(allowed=True, flagged=False, provider="local", categories=[])


# OpenAI moderation API
def _openai_moderate(text: str) -> ModerationResult:
    client = OpenAI()
    resp = client.moderations.create(model="omni-moderation-latest", input=text)
    out = resp.results[0]
    cats = [k for k, v in out.categories.__dict__.items() if v]  # flagged categories
    return ModerationResult(
        allowed=not out.flagged,
        flagged=bool(out.flagged),
        provider="openai",
        categories=cats,
    )


def check_message(text: str) -> ModerationResult:
    """Main entrypoint used by the UI."""
    if not MODERATION_ENABLED:
        return ModerationResult(True, False, provider="disabled", categories=[])

    # If user forces local-only moderation
    if MODERATION_PROVIDER == "local":
        return _local_moderate(text)

    # Default: openai primary + local overlay
    try:
        o = _openai_moderate(text)
    except Exception as e:
        fb = _local_moderate(text)
        fb.error = f"openai_moderation_error: {e.__class__.__name__}"
        return fb

    l = _local_moderate(text)
    if o.flagged or l.flagged:
        cats = list(set(o.categories + l.categories + (["blocklist"] if l.flagged else [])))
        return ModerationResult(allowed=False, flagged=True, provider="openai+local", categories=cats)

    return o
