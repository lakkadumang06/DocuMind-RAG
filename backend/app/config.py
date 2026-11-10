"""Application settings loaded from environment variables and the project .env file.

All tunable values live here so that the rest of the code never reads os.environ directly.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]

Provider = Literal["openai", "anthropic", "gemini", "groq", "ollama"]
EmbeddingProvider = Literal["openai", "gemini", "ollama"]
RetrievalMode = Literal["dense", "bm25", "hybrid"]


class Settings(BaseSettings):
    """Typed configuration for DocuMind. Values come from env vars or the root .env file."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM / embeddings -------------------------------------------------
    llm_provider: Provider = "groq"
    llm_model: str | None = Field(
        default=None, description="Override the provider's default chat model."
    )
    llm_temperature: float = 0.0

    embedding_provider: EmbeddingProvider = "ollama"
    embedding_model: str | None = Field(
        default=None, description="Override the provider's default embedding model."
    )

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    groq_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    # --- Vector store -----------------------------------------------------
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "documind_chunks"

    # --- Ingestion ---------------------------------------------------------
    chunk_size: int = Field(default=800, ge=100, description="Target chunk size in characters.")
    chunk_overlap: int = Field(default=120, ge=0, description="Overlap between chunks.")
    embed_batch_size: int = Field(default=32, ge=1)
    data_dir: Path = REPO_ROOT / "data"
    sample_docs_dir: Path = REPO_ROOT / "data" / "sample_docs"
    index_dir: Path = REPO_ROOT / "data" / "index"

    # --- Retrieval / answering -------------------------------------------
    retrieval_mode: RetrievalMode = "hybrid"
    top_k: int = Field(default=5, ge=1, le=50)
    candidate_k: int = Field(
        default=20, ge=1, description="Candidates fetched per retriever before fusion."
    )
    min_relevance_score: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Below this fused score the assistant refuses to answer.",
    )
    enable_rerank: bool = False

    # --- API -----------------------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]
    log_level: str = "INFO"

    @field_validator(
        "openai_api_key",
        "anthropic_api_key",
        "google_api_key",
        "groq_api_key",
        "qdrant_api_key",
        "llm_model",
        "embedding_model",
        mode="before",
    )
    @classmethod
    def _empty_string_is_none(cls, value: object) -> object:
        """Treat blank values from .env (e.g. 'GROQ_API_KEY=') as not set."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def bm25_index_path(self) -> Path:
        """Location of the persisted BM25 index."""
        return self.index_dir / "bm25.pkl"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (one parse of the environment per process)."""
    settings = Settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return settings
