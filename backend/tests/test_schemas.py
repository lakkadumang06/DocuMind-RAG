"""Tests for the shared Pydantic schemas."""

from __future__ import annotations

import pytest
from app.schemas import ChatAnswer, ChatRequest, Chunk, Citation
from pydantic import ValidationError


def test_chat_request_rejects_empty_question() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(question="")


def test_chat_request_defaults() -> None:
    req = ChatRequest(question="Wie lange ist die Gewährleistung?")
    assert req.session_id is None
    assert req.retrieval_mode is None


def test_chat_answer_confidence_bounds() -> None:
    with pytest.raises(ValidationError):
        ChatAnswer(answer="x", confidence=1.5, answer_found=True)


def test_refusal_answer_round_trip() -> None:
    answer = ChatAnswer(answer="I don't know.", confidence=0.1, answer_found=False)
    data = answer.model_dump()
    assert data["citations"] == []
    assert ChatAnswer.model_validate(data) == answer


def test_citation_from_chunk() -> None:
    chunk = Chunk(
        id="abc:0",
        document_id="abc",
        document_name="warranty_policy.docx",
        chunk_index=0,
        text="The standard warranty period is 24 months.",
        page=1,
        section="2. Warranty period",
        language="en",
    )
    cit = Citation(
        marker=1,
        chunk_id=chunk.id,
        document_id=chunk.document_id,
        document_name=chunk.document_name,
        page=chunk.page,
        section=chunk.section,
        quote=chunk.text,
    )
    assert cit.page == 1
    assert "24 months" in cit.quote
