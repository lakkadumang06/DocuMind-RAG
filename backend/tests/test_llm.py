"""Tests for the provider-agnostic LLM layer (no API calls are made)."""

from __future__ import annotations

import pytest
from app.config import Settings
from app.llm import (
    DEFAULT_CHAT_MODELS,
    DEFAULT_EMBEDDING_MODELS,
    PRICES,
    MissingAPIKeyError,
    UnknownProviderError,
    estimate_cost,
    get_embeddings,
    get_llm,
)


@pytest.mark.parametrize("provider", ["openai", "anthropic", "gemini", "groq"])
def test_hosted_llm_without_key_raises_clear_error(bare_settings: Settings, provider: str) -> None:
    with pytest.raises(MissingAPIKeyError) as exc:
        get_llm(provider=provider, settings=bare_settings)
    assert provider in str(exc.value)
    assert "_API_KEY" in str(exc.value)


@pytest.mark.parametrize("provider", ["openai", "gemini"])
def test_hosted_embeddings_without_key_raises(bare_settings: Settings, provider: str) -> None:
    with pytest.raises(MissingAPIKeyError):
        get_embeddings(provider=provider, settings=bare_settings)


def test_ollama_needs_no_key(bare_settings: Settings) -> None:
    llm = get_llm(provider="ollama", settings=bare_settings)
    emb = get_embeddings(provider="ollama", settings=bare_settings)
    assert llm.model == DEFAULT_CHAT_MODELS["ollama"]
    assert emb.model == DEFAULT_EMBEDDING_MODELS["ollama"]


def test_explicit_model_overrides_default(bare_settings: Settings) -> None:
    llm = get_llm(provider="ollama", model="mistral", settings=bare_settings)
    assert llm.model == "mistral"


def test_unknown_provider(bare_settings: Settings) -> None:
    with pytest.raises(UnknownProviderError):
        get_llm(provider="watson", settings=bare_settings)
    with pytest.raises(UnknownProviderError):
        get_embeddings(provider="anthropic", settings=bare_settings)


def test_every_default_model_has_a_price() -> None:
    for model in {*DEFAULT_CHAT_MODELS.values(), *DEFAULT_EMBEDDING_MODELS.values()}:
        assert model in PRICES, f"missing price for {model}"


def test_estimate_cost() -> None:
    assert estimate_cost("gpt-4.1-mini", 1_000_000, 1_000_000) == pytest.approx(2.0)
    assert estimate_cost("nomic-embed-text", 5000) == 0.0
    assert estimate_cost("does-not-exist", 5000) == 0.0
