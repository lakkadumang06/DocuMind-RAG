"""The RAG answer pipeline: rewrite -> retrieve -> threshold -> generate -> cite.

Both the CLI and the API use ``RagAnswerer.stream()``; ``answer()`` simply drains the
stream. The model writes prose with [n] citation markers and a final "CONFIDENCE: x"
line; we map the markers back to the retrieved chunks to build structured citations.
This keeps one code path for streaming and non-streaming use and works with every
provider, including small local models without tool-calling support.

CLI:  python -m app.rag.answer "Wie lange ist die Gewährleistung?" [--mode hybrid]
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langdetect import LangDetectException, detect

from app.config import Settings, get_settings
from app.rag.memory import ConversationMemory, rewrite_query
from app.rag.prompts import NO_ANSWER_TOKEN, REFUSAL_MESSAGES, SYSTEM_PROMPT, build_user_message
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.rerank import LLMReranker
from app.schemas import ChatAnswer, ChatRequest, Citation, RetrievedChunk

logger = logging.getLogger(__name__)

# Some models (e.g. gpt-oss) write full-width brackets: 【2】 instead of [2].
_MARKER_RE = re.compile(r"[\[【](\d+(?:\s*,\s*\d+)*)[\]】]")
_CONFIDENCE_RE = re.compile(
    r"^\s*CONFIDENCE\s*[:=]\s*([01](?:[.,]\d+)?)\s*$", re.IGNORECASE | re.MULTILINE
)
# Models sometimes append the marker to the last sentence instead of a new line:
# "24 months [1]. CONFIDENCE: 1". This catches it at the very end of the text.
_CONFIDENCE_TAIL_RE = re.compile(r"\s*CONFIDENCE\s*[:=]\s*([01](?:[.,]\d+)?)\s*$", re.IGNORECASE)


@dataclass
class StreamEvent:
    """Either a piece of answer text or the final structured answer."""

    type: Literal["token", "final"]
    token: str = ""
    answer: ChatAnswer | None = None


def detect_query_language(question: str) -> str:
    """'de' or 'en' for a (possibly very short) question; defaults to English."""
    try:
        return "de" if detect(question) == "de" else "en"
    except LangDetectException:
        return "en"


def parse_markers(text: str) -> list[int]:
    """Citation numbers in order of first appearance: 'a [2] b [1, 2]' -> [2, 1]."""
    seen: list[int] = []
    for group in _MARKER_RE.findall(text):
        for raw in group.split(","):
            n = int(raw)
            if n not in seen:
                seen.append(n)
    return seen


def normalise_markers(text: str) -> str:
    """Rewrite full-width citation brackets to plain [n] so the UI can render them."""
    return _MARKER_RE.sub(lambda m: f"[{m.group(1)}]", text)


def parse_confidence(text: str) -> tuple[str, float | None]:
    """Split off the CONFIDENCE marker. Returns (answer_text, confidence or None)."""
    text = normalise_markers(text)
    match = _CONFIDENCE_TAIL_RE.search(text) or _CONFIDENCE_RE.search(text)
    if not match:
        return text.strip(), None
    value = float(match.group(1).replace(",", "."))
    return (text[: match.start()] + text[match.end() :]).strip(), max(0.0, min(1.0, value))


def build_citations(answer_text: str, chunks: list[RetrievedChunk]) -> list[Citation]:
    citations = []
    for marker in parse_markers(answer_text):
        if 1 <= marker <= len(chunks):
            c = chunks[marker - 1].chunk
            citations.append(
                Citation(
                    marker=marker,
                    chunk_id=c.id,
                    document_id=c.document_id,
                    document_name=c.document_name,
                    page=c.page,
                    section=c.section,
                    quote=c.text,
                )
            )
    return citations


class RagAnswerer:
    """Answers questions from the indexed documents, with citations and refusal."""

    def __init__(
        self,
        llm: BaseChatModel,
        retriever: HybridRetriever,
        memory: ConversationMemory | None = None,
        reranker: LLMReranker | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.llm = llm
        self.retriever = retriever
        self.memory = memory or ConversationMemory()
        self.reranker = reranker
        self.settings = settings or get_settings()

    # -- public API -------------------------------------------------------------
    def answer(self, request: ChatRequest) -> ChatAnswer:
        """Non-streaming convenience wrapper around stream()."""
        for event in self.stream(request):
            if event.type == "final" and event.answer is not None:
                return event.answer
        raise RuntimeError("stream ended without a final answer")  # pragma: no cover

    def stream(self, request: ChatRequest) -> Iterator[StreamEvent]:
        language = detect_query_language(request.question)
        query = rewrite_query(self.llm, self.memory, request.session_id, request.question)
        chunks = self.retriever.retrieve(query, mode=request.retrieval_mode, top_k=request.top_k)
        if self.reranker is not None and chunks:
            chunks = self.reranker.rerank(query, chunks)

        relevance = chunks[0].score if chunks else 0.0
        if relevance < self.settings.min_relevance_score:
            logger.info(
                "refusing: top relevance %.3f < %.3f", relevance, self.settings.min_relevance_score
            )
            yield from self._refuse(request, language, chunks, relevance)
            return

        full_text, refused = "", False
        for kind, text in self._generate(query, chunks):
            full_text = text if kind == "done" else full_text
            if kind == "token":
                yield StreamEvent("token", token=text)
            elif kind == "refuse":
                refused = True
        if refused or full_text.strip().startswith(NO_ANSWER_TOKEN):
            yield from self._refuse(request, language, chunks, relevance)
            return

        answer_text, llm_confidence = parse_confidence(full_text)
        citations = build_citations(answer_text, chunks)
        confidence = self._confidence(llm_confidence, relevance, bool(citations))
        answer = ChatAnswer(
            answer=answer_text,
            citations=citations,
            confidence=confidence,
            answer_found=True,
            language=language,
            retrieved=chunks,
            session_id=request.session_id,
        )
        self.memory.add(request.session_id, request.question, answer_text)
        yield StreamEvent("final", answer=answer)

    # -- internals ----------------------------------------------------------------
    def _refuse(
        self, request: ChatRequest, language: str, chunks: list[RetrievedChunk], relevance: float
    ) -> Iterator[StreamEvent]:
        text = REFUSAL_MESSAGES.get(language, REFUSAL_MESSAGES["en"])
        answer = ChatAnswer(
            answer=text,
            citations=[],
            confidence=round(min(relevance, 0.5) * 0.5, 2),
            answer_found=False,
            language=language,
            retrieved=chunks,
            session_id=request.session_id,
        )
        self.memory.add(request.session_id, request.question, text)
        yield StreamEvent("token", token=text)
        yield StreamEvent("final", answer=answer)

    def _generate(self, question: str, chunks: list[RetrievedChunk]) -> Iterator[tuple[str, str]]:
        """Stream the model. Yields ("token", text) for user-visible text, ("refuse", "")
        if the model answered NO_ANSWER, and finally ("done", full_text)."""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=build_user_message(question, chunks)),
        ]
        full = ""
        pending = ""  # text held back until we know it is neither NO_ANSWER nor CONFIDENCE
        decided = False  # have we seen enough text to rule out NO_ANSWER?
        for piece in self.llm.stream(messages):
            # .text flattens content blocks: newer models (e.g. Gemini 3) stream a list of
            # {"type": "text", ...} parts plus thought signatures instead of a plain string.
            text = piece.text
            if not text:
                continue
            full += text
            pending += text
            if not decided:
                stripped = pending.lstrip()
                if len(stripped) < len(NO_ANSWER_TOKEN) and NO_ANSWER_TOKEN.startswith(stripped):
                    continue  # could still become NO_ANSWER, keep buffering
                if stripped.startswith(NO_ANSWER_TOKEN):
                    yield ("refuse", "")
                    return
                decided = True
            # release everything up to the last newline; the last line may be CONFIDENCE
            if "\n" in pending:
                head, pending = pending.rsplit("\n", 1)
                emit = "\n".join(ln for ln in head.split("\n") if not _CONFIDENCE_RE.match(ln))
                if emit:
                    yield ("token", emit + "\n")
        pending = _CONFIDENCE_TAIL_RE.sub("", pending)
        if pending.strip():
            yield ("token", pending)
        yield ("done", full)

    @staticmethod
    def _confidence(llm_confidence: float | None, relevance: float, has_citations: bool) -> float:
        """Blend the model's self-assessment with retrieval relevance.

        Answers without any citation marker are penalised.
        """
        llm_part = 0.5 if llm_confidence is None else llm_confidence
        value = 0.6 * llm_part + 0.4 * min(relevance, 1.0)
        if not has_citations:
            value *= 0.5
        return round(max(0.0, min(1.0, value)), 2)


def build_answerer(settings: Settings | None = None) -> RagAnswerer:
    """Wire the real components together from settings (used by CLI and API)."""
    from app.ingest.store import VectorStore
    from app.llm import get_embeddings, get_llm
    from app.retrieval.bm25 import BM25Retriever
    from app.retrieval.vector import DenseRetriever

    settings = settings or get_settings()
    llm = get_llm(settings=settings)
    store = VectorStore(get_embeddings(settings=settings), settings=settings)
    retriever = HybridRetriever(
        DenseRetriever(store),
        BM25Retriever(path=settings.bm25_index_path),
        default_mode=settings.retrieval_mode,
        top_k=settings.top_k,
        candidate_k=settings.candidate_k,
    )
    reranker = LLMReranker(llm) if settings.enable_rerank else None
    return RagAnswerer(llm, retriever, reranker=reranker, settings=settings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ask DocuMind a question from the terminal.")
    parser.add_argument("question")
    parser.add_argument("--mode", choices=["dense", "bm25", "hybrid"], default=None)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--debug", action="store_true", help="print retrieved chunks and scores")
    args = parser.parse_args(argv)

    answerer = build_answerer()
    request = ChatRequest(question=args.question, retrieval_mode=args.mode, top_k=args.top_k)
    final: ChatAnswer | None = None
    for event in answerer.stream(request):
        if event.type == "token":
            print(event.token, end="", flush=True)
        else:
            final = event.answer
    assert final is not None
    print(f"\n\nanswer_found={final.answer_found}  confidence={final.confidence}", end="")
    print(f"  language={final.language}")
    for c in final.citations:
        where = f"p. {c.page}" if c.page else (c.section or "")
        print(f"  [{c.marker}] {c.document_name} ({where}): {c.quote[:90]!r}...")
    if args.debug:
        print("\nretrieved:")
        for r in final.retrieved:
            ranks = f"dense#{r.dense_rank} bm25#{r.bm25_rank}"
            where = f"{r.chunk.document_name} p{r.chunk.page} {r.chunk.section!r}"
            print(f"  {r.score:.3f} {ranks} {where}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
