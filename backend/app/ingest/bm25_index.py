"""A small BM25 index over chunks, persisted to disk as a pickle.

BM25Plus is used instead of plain Okapi because its IDF never drops to zero on small
corpora (a term found in half of the chunks would otherwise score 0 and trigger a refusal).
rank-bm25 keeps everything in memory, so the index is rebuilt from the stored chunk list
whenever chunks are added or removed. That is fine for thousands of chunks and keeps the
code easy to explain; a real deployment would swap this for OpenSearch or Qdrant sparse
vectors behind the same interface.
"""

from __future__ import annotations

import logging
import pickle
import re
from pathlib import Path

from rank_bm25 import BM25Plus

from app.schemas import Chunk

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)

# Very common English and German function words. Dropping them keeps "wie lange ist die
# Gewährleistung" from matching every German chunk that contains "die" and "ist".
STOPWORDS = frozenset(
    """
    a an the and or of to in on for with is are was were be been by at from as that this
    these those it its do does how what which who when where why much many long
    der die das den dem des ein eine einer eines einem einen und oder von zu im in auf
    für mit ist sind war waren sein bei aus nach dass wie was wer wo wann warum lange
    viel viele welche welcher welches es sich auch nicht
    """.split()
)


def tokenize(text: str) -> list[str]:
    """Lower-case word tokens without stopwords; keeps numbers like '24' and ids like 'hp450'."""
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


class BM25Index:
    """Keyword index over chunks with add / remove / search / save / load."""

    def __init__(self, chunks: list[Chunk] | None = None) -> None:
        self.chunks: list[Chunk] = list(chunks or [])
        self._bm25: BM25Plus | None = None
        self._tokens: list[set[str]] = []
        self._rebuild()

    # -- maintenance ------------------------------------------------------
    def _rebuild(self) -> None:
        corpus = [tokenize(c.text) for c in self.chunks]
        self._tokens = [set(t) for t in corpus]
        self._bm25 = BM25Plus(corpus) if corpus else None

    def add(self, chunks: list[Chunk]) -> None:
        """Add chunks, replacing any existing chunks of the same documents first."""
        doc_ids = {c.document_id for c in chunks}
        self.chunks = [c for c in self.chunks if c.document_id not in doc_ids] + list(chunks)
        self._rebuild()

    def remove_document(self, document_id: str) -> int:
        """Remove every chunk of a document; returns how many were removed."""
        before = len(self.chunks)
        self.chunks = [c for c in self.chunks if c.document_id != document_id]
        self._rebuild()
        return before - len(self.chunks)

    def __len__(self) -> int:
        return len(self.chunks)

    @property
    def document_ids(self) -> set[str]:
        return {c.document_id for c in self.chunks}

    # -- search -----------------------------------------------------------
    def search(self, query: str, k: int = 10) -> list[tuple[Chunk, float]]:
        """Return up to k (chunk, bm25_score) pairs with a positive score, best first."""
        if self._bm25 is None:
            return []
        query_tokens = tokenize(query)
        scores = self._bm25.get_scores(query_tokens)
        wanted = set(query_tokens)
        # BM25Plus gives every chunk a small positive score for each query term found
        # anywhere in the corpus, so rank only chunks that share a token with the query.
        candidates = [i for i, toks in enumerate(self._tokens) if wanted & toks]
        ranked = sorted(candidates, key=lambda i: scores[i], reverse=True)
        return [(self.chunks[i], float(scores[i])) for i in ranked[:k]]

    # -- persistence ------------------------------------------------------
    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            pickle.dump([c.model_dump() for c in self.chunks], fh)
        logger.debug("saved BM25 index with %d chunks to %s", len(self.chunks), path)

    @classmethod
    def load(cls, path: Path) -> BM25Index:
        """Load an index from disk; a missing file yields an empty index."""
        if not path.exists():
            return cls()
        with path.open("rb") as fh:
            raw = pickle.load(fh)  # noqa: S301 - file is written by us, not user input
        return cls([Chunk.model_validate(r) for r in raw])
