"""Pydantic models shared by ingestion, retrieval, answering and the API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RetrievalMode = Literal["dense", "bm25", "hybrid"]


class DocumentInfo(BaseModel):
    """Metadata about an ingested document."""

    id: str = Field(description="Stable id, derived from the SHA-256 of the file content.")
    filename: str
    file_type: Literal["pdf", "docx", "txt"]
    language: str = Field(description="ISO 639-1 code of the dominant language, e.g. 'de'.")
    num_pages: int = Field(ge=0)
    num_chunks: int = Field(ge=0)
    size_bytes: int = Field(ge=0)
    ingested_at: datetime


class Chunk(BaseModel):
    """A piece of a document with the metadata needed for citations."""

    id: str = Field(description="Deterministic id: '<document_id>:<chunk_index>'.")
    document_id: str
    document_name: str
    chunk_index: int = Field(ge=0)
    text: str
    page: int | None = Field(default=None, description="1-based page number, if known.")
    section: str | None = Field(default=None, description="Nearest heading above the chunk.")
    language: str = "en"


class RetrievedChunk(BaseModel):
    """A chunk returned by a retriever together with its score."""

    chunk: Chunk
    score: float = Field(description="Fused or raw relevance score, higher is better.")
    dense_rank: int | None = None
    bm25_rank: int | None = None


class Citation(BaseModel):
    """A pointer to the exact passage that supports part of an answer."""

    document_id: str
    document_name: str
    page: int | None = None
    section: str | None = None
    quote: str = Field(description="Verbatim excerpt from the source chunk.")


class ChatRequest(BaseModel):
    """A user question and how to answer it."""

    question: str = Field(min_length=1, max_length=4000)
    session_id: str | None = Field(
        default=None, description="Reuse to keep conversation memory for follow-up questions."
    )
    retrieval_mode: RetrievalMode | None = Field(
        default=None, description="Override the configured retrieval mode."
    )
    top_k: int | None = Field(default=None, ge=1, le=20)


class ChatAnswer(BaseModel):
    """Structured answer returned by the RAG pipeline."""

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    answer_found: bool = Field(
        description="False when the documents do not contain the answer and we refused."
    )
    language: str = Field(default="en", description="Language of the answer (ISO 639-1).")
    retrieved: list[RetrievedChunk] = Field(
        default_factory=list, description="Chunks shown in the retrieval debug panel."
    )
    session_id: str | None = None


class HealthResponse(BaseModel):
    """Response of GET /health."""

    status: Literal["ok", "degraded"]
    llm_provider: str
    embedding_provider: str
    qdrant_reachable: bool
    documents: int = 0
