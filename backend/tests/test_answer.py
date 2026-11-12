"""Answer pipeline tests with a fake LLM and in-memory retrieval. No network, no keys."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.config import Settings
from app.ingest.pipeline import IngestionPipeline
from app.ingest.store import VectorStore
from app.rag.answer import (
    RagAnswerer,
    build_citations,
    detect_query_language,
    parse_confidence,
    parse_markers,
)
from app.rag.memory import ConversationMemory, rewrite_query
from app.rag.prompts import NO_ANSWER_TOKEN, REFUSAL_MESSAGES
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.vector import DenseRetriever
from app.schemas import ChatRequest
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult


@pytest.fixture
def retriever(
    txt_file: Path, docx_file: Path, memory_store: VectorStore, test_settings: Settings
) -> HybridRetriever:
    pipeline = IngestionPipeline(memory_store.embeddings, memory_store, settings=test_settings)
    pipeline.ingest_directory(txt_file.parent)
    return HybridRetriever(
        DenseRetriever(memory_store),
        BM25Retriever(index=pipeline.bm25),
        default_mode="bm25",
        top_k=3,
    )


def _answerer(responses: list[str], retriever: HybridRetriever, settings: Settings) -> RagAnswerer:
    return RagAnswerer(FakeListChatModel(responses=responses), retriever, settings=settings)


def test_parse_helpers() -> None:
    assert parse_markers("24 months [2]. Also [1, 2] and [3].") == [2, 1, 3]
    text, conf = parse_confidence("The answer [1].\nCONFIDENCE: 0.85\n")
    assert text == "The answer [1]." and conf == 0.85
    assert parse_confidence("no line") == ("no line", None)
    assert parse_confidence("x\nConfidence: 1,0")[1] == 1.0


def test_detect_query_language() -> None:
    assert detect_query_language("Wie lange ist die Gewährleistung für Hydraulikpumpen?") == "de"
    assert detect_query_language("How long is the warranty for hydraulic pumps?") == "en"


def test_english_answer_with_citations(retriever: HybridRetriever, test_settings: Settings) -> None:
    answerer = _answerer(
        ["The standard warranty is 24 months from delivery [1].\nCONFIDENCE: 0.9"],
        retriever,
        test_settings,
    )
    result = answerer.answer(ChatRequest(question="How long is the standard warranty period?"))
    assert result.answer_found is True
    assert result.language == "en"
    assert result.answer == "The standard warranty is 24 months from delivery [1]."
    assert "CONFIDENCE" not in result.answer
    assert [c.marker for c in result.citations] == [1]
    assert result.citations[0].chunk_id == result.retrieved[0].chunk.id
    assert "24 months" in result.citations[0].quote
    assert 0.5 < result.confidence <= 1.0
    assert 1 <= len(result.retrieved) <= 3


def test_streaming_hides_confidence_line(
    retriever: HybridRetriever, test_settings: Settings
) -> None:
    answerer = _answerer(
        ["Line one [1].\nLine two [1].\nCONFIDENCE: 0.7"], retriever, test_settings
    )
    events = list(answerer.stream(ChatRequest(question="warranty period months")))
    tokens = "".join(e.token for e in events if e.type == "token")
    assert tokens.strip() == "Line one [1].\nLine two [1]."
    assert events[-1].type == "final" and events[-1].answer is not None
    assert events[-1].answer.confidence > 0


def test_model_no_answer_becomes_refusal(
    retriever: HybridRetriever, test_settings: Settings
) -> None:
    answerer = _answerer([f"{NO_ANSWER_TOKEN}\nCONFIDENCE: 0.1"], retriever, test_settings)
    events = list(
        answerer.stream(ChatRequest(question="Wie hoch ist die Deckungssumme der Versicherung?"))
    )
    tokens = "".join(e.token for e in events if e.type == "token")
    final = events[-1].answer
    assert final is not None and final.answer_found is False
    assert final.language == "de" and tokens == REFUSAL_MESSAGES["de"] == final.answer
    assert final.citations == [] and final.confidence < 0.3
    assert final.retrieved  # debug panel still shows what was retrieved


def test_low_relevance_refuses_without_calling_llm(
    retriever: HybridRetriever, test_settings: Settings
) -> None:
    strict = test_settings.model_copy(update={"min_relevance_score": 0.99})
    llm = FakeListChatModel(responses=["SHOULD NOT BE USED"])
    answerer = RagAnswerer(llm, retriever, settings=strict)
    result = answerer.answer(ChatRequest(question="How long is the warranty?"))
    assert result.answer_found is False
    assert result.answer == REFUSAL_MESSAGES["en"]
    assert llm.i == 0  # FakeListChatModel counts consumed responses


def test_no_results_refuses(retriever: HybridRetriever, test_settings: Settings) -> None:
    answerer = _answerer(["unused"], retriever, test_settings)
    result = answerer.answer(ChatRequest(question="zzzz qqqq", retrieval_mode="bm25"))
    assert result.answer_found is False and result.retrieved == []


def test_missing_citations_halves_confidence(
    retriever: HybridRetriever, test_settings: Settings
) -> None:
    cited = _answerer(["24 months [1].\nCONFIDENCE: 0.8"], retriever, test_settings)
    uncited = _answerer(["24 months.\nCONFIDENCE: 0.8"], retriever, test_settings)
    q = ChatRequest(question="How long is the warranty period?")
    assert uncited.answer(q).confidence < cited.answer(q).confidence
    assert build_citations("no markers", []) == []


def test_memory_and_query_rewrite(retriever: HybridRetriever, test_settings: Settings) -> None:
    memory = ConversationMemory(max_turns=2)
    llm = FakeListChatModel(responses=["How long is the warranty for power supplies?"])
    assert rewrite_query(llm, memory, "s1", "and for power supplies?") == "and for power supplies?"
    memory.add("s1", "How long is the warranty?", "24 months [1].")
    assert rewrite_query(llm, memory, "s1", "and for power supplies?") == (
        "How long is the warranty for power supplies?"
    )
    memory.add("s1", "q2", "a2")
    memory.add("s1", "q3", "a3")
    assert [t.question for t in memory.history("s1")] == ["q2", "q3"]
    assert memory.history(None) == [] and memory.history("unknown") == []
    memory.clear("s1")
    assert memory.history("s1") == []


def test_follow_up_uses_rewritten_query(
    retriever: HybridRetriever, test_settings: Settings
) -> None:
    # 1st response: answer; 2nd: rewrite; 3rd: answer to the follow-up
    llm = FakeListChatModel(
        responses=[
            "24 months [1].\nCONFIDENCE: 0.9",
            "How many working days until an RMA number is issued?",
            "Within 2 working days [1].\nCONFIDENCE: 0.8",
        ]
    )
    answerer = RagAnswerer(llm, retriever, settings=test_settings)
    first = answerer.answer(
        ChatRequest(question="How long is the warranty period?", session_id="s")
    )
    second = answerer.answer(ChatRequest(question="and the RMA?", session_id="s"))
    assert first.answer_found and second.answer_found
    assert "RMA" in second.citations[0].quote
    assert len(answerer.memory.history("s")) == 2


def test_inline_confidence_is_stripped(retriever: HybridRetriever, test_settings: Settings) -> None:
    # model forgot the newline before the marker
    answerer = _answerer(
        ["The warranty is 24 months [1]. CONFIDENCE: 0.9"], retriever, test_settings
    )
    events = list(answerer.stream(ChatRequest(question="How long is the warranty period?")))
    tokens = "".join(e.token for e in events if e.type == "token")
    final = events[-1].answer
    assert final is not None
    assert final.answer == "The warranty is 24 months [1]."
    assert "CONFIDENCE" not in tokens
    assert parse_confidence("x [1]. Confidence: 0,8") == ("x [1].", 0.8)


class _ContentBlockModel(BaseChatModel):
    """Fake model that streams list-of-blocks content like Gemini 3 does."""

    reply: str

    @property
    def _llm_type(self) -> str:
        return "content-blocks"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):  # noqa: ANN001
        block = [{"type": "text", "text": self.reply}]
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=block))])

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):  # noqa: ANN001
        for word in self.reply.split(" "):
            part = [{"type": "text", "text": word + " ", "index": 0}]
            yield ChatGenerationChunk(message=AIMessageChunk(content=part))
        signature = [{"type": "text", "text": "", "extras": {"signature": "abc"}, "index": 0}]
        yield ChatGenerationChunk(message=AIMessageChunk(content=signature))


def test_content_block_models_stream_plain_text(
    retriever: HybridRetriever, test_settings: Settings
) -> None:
    llm = _ContentBlockModel(reply="24 months [1].\nCONFIDENCE: 0.9")
    answerer = RagAnswerer(llm, retriever, settings=test_settings)
    events = list(answerer.stream(ChatRequest(question="How long is the warranty period?")))
    tokens = "".join(e.token for e in events if e.type == "token")
    final = events[-1].answer
    assert final is not None and final.answer_found
    assert "{'type'" not in tokens and "signature" not in tokens
    assert tokens.strip() == final.answer == "24 months [1]."
    assert final.citations and final.confidence > 0.7


def test_full_width_citation_brackets_are_accepted() -> None:
    """gpt-oss style 【2】 markers count as citations and are normalised to [2]."""
    assert parse_markers("Frist 24 Monate【2】, siehe auch 【1, 3】.") == [2, 1, 3]
    text, conf = parse_confidence("Frist 24 Monate【2】.\nCONFIDENCE: 0.8")
    assert text == "Frist 24 Monate[2]."
    assert conf == 0.8
