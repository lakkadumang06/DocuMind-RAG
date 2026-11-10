"""Keyword retrieval with BM25 over the on-disk index built during ingestion."""

from __future__ import annotations

import logging
from pathlib import Path

from app.ingest.bm25_index import BM25Index
from app.schemas import RetrievedChunk

logger = logging.getLogger(__name__)

# BM25 scores are unbounded; score / (score + SATURATION) maps them into [0, 1) so the
# same relevance threshold can be used for every retrieval mode. A score of 5 -> 0.5.
SATURATION = 5.0


def normalise_bm25(score: float) -> float:
    return score / (score + SATURATION) if score > 0 else 0.0


class BM25Retriever:
    """Searches a BM25Index; call reload() after ingestion changed the index on disk."""

    def __init__(self, index: BM25Index | None = None, path: Path | None = None) -> None:
        if index is None and path is None:
            raise ValueError("BM25Retriever needs an index or a path to load one from")
        self.path = path
        self.index = index if index is not None else BM25Index.load(path)  # type: ignore[arg-type]

    def reload(self) -> None:
        if self.path is not None:
            self.index = BM25Index.load(self.path)

    def retrieve(self, query: str, k: int) -> list[RetrievedChunk]:
        hits = self.index.search(query, k=k)
        results = [
            RetrievedChunk(chunk=chunk, score=normalise_bm25(raw), bm25_rank=rank, bm25_score=raw)
            for rank, (chunk, raw) in enumerate(hits, start=1)
        ]
        logger.debug("bm25: %d hits for %r", len(results), query)
        return results
