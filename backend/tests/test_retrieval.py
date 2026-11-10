"""Retrieval tests: RRF math, BM25 normalisation and mode dispatch."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.config import Settings
from app.ingest.pipeline import IngestionPipeline
from app.ingest.store import VectorStore
from app.retrieval.bm25 import BM25Retriever, normalise_bm25
from app.retrieval.hybrid import HybridRetriever, reciprocal_rank_fusion
from app.retrieval.rerank import _parse_scores
from app.retrieval.vector import DenseRetriever
from app.schemas import Chunk, RetrievedChunk


def _rc(
    cid: str, score: float, dense_rank: int | None = None, bm25_rank: int | None = None
) -> RetrievedChunk:
    chunk = Chunk(id=cid, document_id="d", document_name="d.txt", chunk_index=0, text=cid)
    return RetrievedChunk(chunk=chunk, score=score, dense_rank=dense_rank, bm25_rank=bm25_rank)


def test_rrf_prefers_chunks_found_by_both_retrievers() -> None:
    dense = [_rc("a", 0.9, dense_rank=1), _rc("b", 0.8, dense_rank=2), _rc("c", 0.7, dense_rank=3)]
    bm25 = [_rc("c", 0.6, bm25_rank=1), _rc("b", 0.5, bm25_rank=2), _rc("x", 0.4, bm25_rank=3)]
    fused = reciprocal_rank_fusion([dense, bm25])
    ids = [r.chunk.id for r in fused]
    assert ids[0] in {"b", "c"}  # both appear in both lists
    assert ids.index("x") == 3 and ids.index("a") in (1, 2)
    b = next(r for r in fused if r.chunk.id == "b")
    assert b.dense_rank == 2 and b.bm25_rank == 2
    assert 0.0 < fused[-1].score < fused[0].score <= 1.0


def test_rrf_perfect_agreement_scores_one() -> None:
    fused = reciprocal_rank_fusion([[_rc("a", 1.0, dense_rank=1)], [_rc("a", 1.0, bm25_rank=1)]])
    assert fused[0].score == 1.0
    assert reciprocal_rank_fusion([]) == []


def test_bm25_normalisation() -> None:
    assert normalise_bm25(0.0) == 0.0
    assert normalise_bm25(5.0) == pytest.approx(0.5)
    assert 0.0 < normalise_bm25(1.0) < normalise_bm25(100.0) < 1.0


def test_hybrid_modes_on_fixtures(
    txt_file: Path,
    docx_file: Path,
    pdf_file: Path,
    memory_store: VectorStore,
    test_settings: Settings,
) -> None:
    pipeline = IngestionPipeline(memory_store.embeddings, memory_store, settings=test_settings)
    pipeline.ingest_directory(txt_file.parent)
    retriever = HybridRetriever(
        DenseRetriever(memory_store),
        BM25Retriever(index=pipeline.bm25),
        default_mode="hybrid",
        top_k=3,
        candidate_k=10,
    )
    bm25 = retriever.retrieve("RMA number working days", mode="bm25")
    assert bm25 and "RMA" in bm25[0].chunk.text and bm25[0].bm25_rank == 1
    dense = retriever.retrieve("RMA number", mode="dense")
    assert len(dense) == 3 and all(r.dense_rank for r in dense)
    hybrid = retriever.retrieve("RMA number working days")
    assert len(hybrid) <= 3 and any("RMA" in r.chunk.text for r in hybrid)
    with pytest.raises(ValueError):
        retriever.retrieve("x", mode="magic")  # type: ignore[arg-type]


def test_rerank_score_parsing() -> None:
    assert _parse_scores('Sure: {"1": 8, "2": "0", "9": 5, "x": 1}', n=3) == {1: 8.0, 2: 0.0}
    assert _parse_scores("no json here", n=3) == {}
    assert _parse_scores('{"1": 15}', n=1) == {1: 10.0}
