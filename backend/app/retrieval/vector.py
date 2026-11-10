"""Dense retrieval: embed the query and search Qdrant by cosine similarity."""

from __future__ import annotations

import logging

from app.ingest.store import VectorStore
from app.schemas import RetrievedChunk

logger = logging.getLogger(__name__)


class DenseRetriever:
    """Wraps VectorStore.search and returns RetrievedChunk objects with ranks."""

    def __init__(self, store: VectorStore) -> None:
        self.store = store

    def retrieve(self, query: str, k: int) -> list[RetrievedChunk]:
        hits = self.store.search(query, k=k)
        results = [
            RetrievedChunk(
                chunk=chunk,
                score=max(0.0, min(1.0, similarity)),  # cosine similarity already in [0, 1]
                dense_rank=rank,
                dense_score=similarity,
            )
            for rank, (chunk, similarity) in enumerate(hits, start=1)
        ]
        logger.debug("dense: %d hits for %r", len(results), query)
        return results
