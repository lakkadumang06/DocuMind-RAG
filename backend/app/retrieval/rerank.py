"""Optional LLM-based re-ranking of retrieved chunks (ENABLE_RERANK=false by default).

Re-ranking costs one extra LLM call per question, which roughly doubles latency. It helps
when the top-k from retrieval contains near-duplicates or chunks that merely share
keywords with the question. A cross-encoder (e.g. bge-reranker) would be faster, but it
would add a heavy dependency; the LLM variant keeps the provider-agnostic design.
"""

from __future__ import annotations

import json
import logging
import re

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.schemas import RetrievedChunk

logger = logging.getLogger(__name__)

RERANK_SYSTEM = (
    "You grade how useful text passages are for answering a question. "
    "Reply ONLY with a JSON object mapping passage number to a relevance score "
    'from 0 (irrelevant) to 10 (contains the full answer). Example: {"1": 8, "2": 0}'
)


def _parse_scores(text: str, n: int) -> dict[int, float]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    scores: dict[int, float] = {}
    for key, value in raw.items():
        try:
            idx, score = int(key), float(value)
        except (TypeError, ValueError):
            continue
        if 1 <= idx <= n:
            scores[idx] = max(0.0, min(10.0, score))
    return scores


class LLMReranker:
    """Re-orders chunks by an LLM relevance grade; falls back to the input order on errors."""

    def __init__(self, llm: BaseChatModel) -> None:
        self.llm = llm

    def rerank(self, question: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if len(chunks) < 2:
            return chunks
        passages = "\n\n".join(
            f"[{i}] ({c.chunk.document_name}) {c.chunk.text[:800]}"
            for i, c in enumerate(chunks, start=1)
        )
        messages = [
            SystemMessage(content=RERANK_SYSTEM),
            HumanMessage(content=f"Question: {question}\n\nPassages:\n{passages}"),
        ]
        try:
            response = self.llm.invoke(messages)
            scores = _parse_scores(response.text, len(chunks))
        except Exception as exc:  # noqa: BLE001 - never let re-ranking break answering
            logger.warning("re-ranking failed, keeping retrieval order: %s", exc)
            return chunks
        if not scores:
            return chunks
        reranked = []
        for i, item in enumerate(chunks, start=1):
            grade = scores.get(i, 0.0) / 10.0
            copy = item.model_copy()
            copy.score = round(0.5 * item.score + 0.5 * grade, 4)  # blend, don't replace
            reranked.append(copy)
        return sorted(reranked, key=lambda r: r.score, reverse=True)
