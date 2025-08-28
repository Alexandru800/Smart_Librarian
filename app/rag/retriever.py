from __future__ import annotations
import chromadb
from typing import List, Dict, Any, Optional

from app.config import CHROMADB_PATH, CHROMA_COLLECTION, RETRIEVER_TOP_K
from app.llm.openai_client import embed_text


class BooksRetriever:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=str(CHROMADB_PATH))
        self.collection = self.client.get_collection(CHROMA_COLLECTION)

    # Search for the top K relevant book summaries based on the query
    def search(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        k = top_k or RETRIEVER_TOP_K
        q_emb = embed_text(query)
        res = self.collection.query(
            query_embeddings=[q_emb],
            n_results=k,
            include=["metadatas", "documents", "distances"],
        )

        items: List[Dict[str, Any]] = []
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        ids_block = res.get("ids", [[]])  # may or may not be present
        ids = ids_block[0] if ids_block else [None] * len(docs)

        for i in range(len(docs)):
            if dists[i] < 0.8:  # filter out low-confidence results
                items.append({
                    "id": ids[i],  # may be None on some versions
                    "title": metas[i].get("title"),
                    "document": docs[i],
                    "distance": dists[i],
                })
        return items

    # Get the best matching title for a given query (smoke test)
    def best_title(self, query: str) -> Optional[str]:
        items = self.search(query, top_k=1)
        return items[0]["title"] if items else None
