"""Hybrid retrieval: dense + BM25 merged with Reciprocal Rank Fusion (RRF).

Why both? Embeddings understand paraphrases and cross-language questions ("warranty" vs
"Gewährleistung"), BM25 nails exact identifiers like "RA-HP 450" or "ISO 4406". RRF
needs no score calibration between the two: each list contributes 1 / (K + rank).
"""

from __future__ import annotations

import logging
from typing import Literal

from app.retrieval.bm25 import BM25Retriever
from app.retrieval.vector import DenseRetriever
from app.schemas import RetrievedChunk

logger = logging.getLogger(__name__)

RetrievalMode = Literal["dense", "bm25", "hybrid"]
RRF_K = 60  # the constant from the original RRF paper; dampens the top-rank bonus


def reciprocal_rank_fusion(
    ranked_lists: list[list[RetrievedChunk]], k: int = RRF_K
) -> list[RetrievedChunk]:
    """Merge ranked lists. The fused score is normalised so that a chunk ranked first in
    every list gets 1.0 and one that appears first in a single list gets 1/len(lists)."""
    if not ranked_lists:
        return []
    best_possible = len(ranked_lists) / (k + 1)
    fused: dict[str, RetrievedChunk] = {}
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked, start=1):
            cid = item.chunk.id
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
            if cid in fused:  # merge rank/score info from the other retriever
                merged = fused[cid]
                merged.dense_rank = merged.dense_rank or item.dense_rank
                merged.bm25_rank = merged.bm25_rank or item.bm25_rank
                merged.dense_score = merged.dense_score or item.dense_score
                merged.bm25_score = merged.bm25_score or item.bm25_score
            else:
                fused[cid] = item.model_copy()
    for cid, item in fused.items():
        item.score = round(scores[cid] / best_possible, 4)
    return sorted(fused.values(), key=lambda r: r.score, reverse=True)


class HybridRetriever:
    """Single entry point for retrieval in any mode."""

    def __init__(
        self,
        dense: DenseRetriever,
        bm25: BM25Retriever,
        default_mode: RetrievalMode = "hybrid",
        top_k: int = 5,
        candidate_k: int = 20,
    ) -> None:
        self.dense = dense
        self.bm25 = bm25
        self.default_mode = default_mode
        self.top_k = top_k
        self.candidate_k = candidate_k

    def retrieve(
        self, query: str, mode: RetrievalMode | None = None, top_k: int | None = None
    ) -> list[RetrievedChunk]:
        mode = mode or self.default_mode
        top_k = top_k or self.top_k
        if mode == "dense":
            results = self.dense.retrieve(query, k=top_k)
        elif mode == "bm25":
            results = self.bm25.retrieve(query, k=top_k)
        elif mode == "hybrid":
            dense = self.dense.retrieve(query, k=self.candidate_k)
            keyword = self.bm25.retrieve(query, k=self.candidate_k)
            results = reciprocal_rank_fusion([dense, keyword])[:top_k]
        else:
            raise ValueError(f"unknown retrieval mode {mode!r}")
        logger.info("retrieve(%s) %r -> %d chunks", mode, query[:60], len(results))
        return results
