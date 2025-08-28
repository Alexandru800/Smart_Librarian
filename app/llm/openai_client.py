from typing import List
from openai import OpenAI

from app.config import OPENAI_EMBED_MODEL, OPENAI_CHAT_MODEL

_client = OpenAI()

def embed_text(text: str) -> List[float]:
    """
    Returns an embedding vector for the given text using OpenAI's embeddings API.
    """
    resp = _client.embeddings.create(model=OPENAI_EMBED_MODEL, input=text)
    return resp.data[0].embedding

def chat_once(messages: list[dict], temperature: float = 0.7, max_tokens: int = 250):
    """
    Single-shot chat completion. Returns the full text.
    """
    resp = _client.chat.completions.create(
        model=OPENAI_CHAT_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=False,
    )
    return resp.choices[0].message.content or ""