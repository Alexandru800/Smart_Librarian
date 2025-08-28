import os
import json
from pathlib import Path
import pytest

from app.rag.retriever import BooksRetriever
from app.config import BOOK_SUMMARIES_PATH

# Skip tests if the OpenAI key is missing (embeddings are needed for queries)
requires_api = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)

@requires_api
def test_retriever_has_vectors_and_returns_top1():
    r = BooksRetriever()

    # If the collection is empty, guide the user to run ingest first.
    try:
        count = r.collection.count()
    except Exception:
        count = 0
    if count == 0:
        pytest.skip("Chroma collection empty. Run the ingest script first.")

    # Use the first title as a deterministic query (simple smoke test)
    data = json.loads(Path(BOOK_SUMMARIES_PATH).read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) > 0

    title = data[0]["title"]
    items = r.search(title, top_k=1)

    assert isinstance(items, list)
    assert len(items) == 1
    top = items[0]
    # Basic structure checks
    for key in ("id", "title", "document", "distance"):
        assert key in top

    # The top result should be one of the dataset titles (usually the same as the query)
    all_titles = {b["title"] for b in data}
    assert top["title"] in all_titles

    # best_title() should agree with search(..., top_k=1)
    assert r.best_title(title) == top["title"]
