"""
Loads data/book_summaries.json, derives a short summary,
creates a Chroma collection "books", and upserts vectors using OpenAI embeddings.
Re-running this script wipes the collection and rebuilds it.
"""
from __future__ import annotations
import json
import re
import chromadb
from pathlib import Path

from app.config import BOOK_SUMMARIES_PATH, CHROMADB_PATH, CHROMA_COLLECTION
from app.llm.openai_client import embed_text


def slugify(title: str) -> str:
    s = title.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def to_short(text: str, max_sentences: int = 3, max_chars: int = 250) -> str:
    # naive sentence split; good enough for our curated data
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    short = " ".join(parts[:max_sentences]).strip()
    if len(short) > max_chars:
        short = short[: max_chars - 1].rstrip() + "…"
    return short


def main() -> None:
    # 1) Load JSON
    path = Path(BOOK_SUMMARIES_PATH)
    records = json.loads(path.read_text(encoding="utf-8"))

    # 2) Create persistent Chroma client & wipe collection
    CHROMADB_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMADB_PATH))

    # delete if exists (idempotent-ingest)
    try:
        client.delete_collection(CHROMA_COLLECTION)
    except Exception:
        pass

    collection = client.create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"}  # cosine distance
    )

    # 3) Build docs, embeddings, and add
    ids, docs, metas, embeds = [], [], [], []
    for rec in records:
        title = rec["title"]
        full = rec["summary"]
        short = to_short(full)

        doc_text = f"Title: {title}\nSummary: {short}"
        vec = embed_text(doc_text)

        ids.append(slugify(title))
        docs.append(doc_text)
        metas.append({"title": title})
        embeds.append(vec)

    if ids:
        collection.add(ids=ids, documents=docs, metadatas=metas, embeddings=embeds)

    print(f"Ingested {len(ids)} books into '{CHROMA_COLLECTION}' at {CHROMADB_PATH}")


if __name__ == "__main__":
    main()
