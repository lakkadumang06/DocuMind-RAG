"""Model-agnostic access to chat models and embeddings.

This is the ONLY module that imports provider SDKs. Everything else calls
``get_llm()`` / ``get_embeddings()`` and works with LangChain's generic
``BaseChatModel`` and ``Embeddings`` interfaces, so the provider can be switched
by changing two environment variables.

Trade-off worth remembering for interviews: local Ollama keeps documents on the
machine (no data leaves the company) but is slow on a laptop; hosted providers
are fast and cheap per request but send chunk text to a third party.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

DEFAULT_CHAT_MODELS: dict[str, str] = {
    "openai": "gpt-4.1-mini",
    "anthropic": "claude-sonnet-5-5",
    "gemini": "gemini-2.5-flash",
    "groq": "llama-3.3-70b-versatile",
    "ollama": "qwen3:8b",
}

DEFAULT_EMBEDDING_MODELS: dict[str, str] = {
    "openai": "text-embedding-3-small",
    "gemini": "gemini-embedding-001",
    "ollama": "nomic-embed-text",
}


@dataclass(frozen=True)
class Price:
    """Approximate list price in USD per 1 million tokens."""

    input_per_million: float
    output_per_million: float = 0.0


# Approximate public list prices (USD per 1M tokens). Checked November 2026; they
# change often, so treat cost numbers in the evals as estimates, not invoices.
PRICES: dict[str, Price] = {
    # chat models
    "gpt-4.1-mini": Price(0.40, 1.60),
    "gpt-4.1": Price(2.00, 8.00),
    "claude-sonnet-5-5": Price(3.00, 15.00),
    "claude-haiku-5-5": Price(1.00, 5.00),
    "gemini-2.5-flash": Price(0.30, 2.50),
    "gemini-2.5-pro": Price(1.25, 10.00),
    "llama-3.3-70b-versatile": Price(0.59, 0.79),
    "llama-3.1-8b-instant": Price(0.05, 0.08),
    # embedding models
    "text-embedding-3-small": Price(0.02),
    "text-embedding-3-large": Price(0.13),
    "gemini-embedding-001": Price(0.15),
    # local models cost electricity, not dollars
    "qwen3:8b": Price(0.0, 0.0),
    "nomic-embed-text": Price(0.0),
}


class MissingAPIKeyError(RuntimeError):
    """Raised when the selected provider needs an API key that is not configured."""


class UnknownProviderError(ValueError):
    """Raised when LLM_PROVIDER / EMBEDDING_PROVIDER has an unsupported value."""


def _require_key(value: str | None, env_name: str, provider: str) -> str:
    if not value:
        raise MissingAPIKeyError(
            f"Provider '{provider}' needs {env_name}. Add it to .env (see .env.example) "
            f"or choose another provider, e.g. LLM_PROVIDER=ollama for a local model."
        )
    return value


def get_llm(
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    settings: Settings | None = None,
) -> BaseChatModel:
    """Return a LangChain chat model for the configured (or given) provider.

    Args:
        provider: one of openai, anthropic, gemini, groq, ollama. Defaults to LLM_PROVIDER.
        model: model name; defaults to LLM_MODEL or the provider default.
        temperature: sampling temperature; defaults to LLM_TEMPERATURE (0 for RAG).
        settings: injected settings, mainly for tests.
    """
    settings = settings or get_settings()
    provider = (provider or settings.llm_provider).lower()
    model = model or settings.llm_model or DEFAULT_CHAT_MODELS.get(provider)
    temperature = settings.llm_temperature if temperature is None else temperature
    if model is None:
        raise UnknownProviderError(f"Unknown LLM provider '{provider}'.")
    logger.info("Using chat model %s via %s", model, provider)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        key = _require_key(settings.openai_api_key, "OPENAI_API_KEY", provider)
        return ChatOpenAI(model=model, temperature=temperature, api_key=key)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        key = _require_key(settings.anthropic_api_key, "ANTHROPIC_API_KEY", provider)
        return ChatAnthropic(model=model, temperature=temperature, api_key=key)

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        key = _require_key(settings.google_api_key, "GOOGLE_API_KEY", provider)
        return ChatGoogleGenerativeAI(model=model, temperature=temperature, google_api_key=key)

    if provider == "groq":
        from langchain_groq import ChatGroq

        key = _require_key(settings.groq_api_key, "GROQ_API_KEY", provider)
        return ChatGroq(model=model, temperature=temperature, api_key=key)

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        # reasoning=False turns off the <think> blocks of models like qwen3; RAG answers
        # should be grounded in the context, not in long hidden deliberation.
        return ChatOllama(
            model=model, temperature=temperature, base_url=settings.ollama_base_url, reasoning=False
        )

    raise UnknownProviderError(f"Unknown LLM provider '{provider}'.")


def get_embeddings(
    provider: str | None = None,
    model: str | None = None,
    settings: Settings | None = None,
) -> Embeddings:
    """Return a LangChain embeddings model for the configured (or given) provider.

    Anthropic and Groq offer no embedding models, so the embedding provider is
    configured separately (EMBEDDING_PROVIDER = openai | gemini | ollama).
    """
    settings = settings or get_settings()
    provider = (provider or settings.embedding_provider).lower()
    model = model or settings.embedding_model or DEFAULT_EMBEDDING_MODELS.get(provider)
    if model is None:
        raise UnknownProviderError(
            f"Unknown embedding provider '{provider}'. Use openai, gemini or ollama."
        )
    logger.info("Using embedding model %s via %s", model, provider)

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        key = _require_key(settings.openai_api_key, "OPENAI_API_KEY", provider)
        return OpenAIEmbeddings(model=model, api_key=key)

    if provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        key = _require_key(settings.google_api_key, "GOOGLE_API_KEY", provider)
        return GoogleGenerativeAIEmbeddings(model=model, google_api_key=key)

    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(model=model, base_url=settings.ollama_base_url)

    raise UnknownProviderError(
        f"Unknown embedding provider '{provider}'. Use openai, gemini or ollama."
    )


def estimate_cost(model: str, input_tokens: int, output_tokens: int = 0) -> float:
    """Approximate USD cost of one call. Unknown models cost 0 and log a warning."""
    price = PRICES.get(model)
    if price is None:
        logger.warning("No price entry for model %s; reporting cost 0", model)
        return 0.0
    return (
        input_tokens * price.input_per_million + output_tokens * price.output_per_million
    ) / 1_000_000
