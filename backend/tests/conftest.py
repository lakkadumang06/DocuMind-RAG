"""Shared pytest fixtures. Tests must run without API keys or network."""

from __future__ import annotations

import pytest
from app.config import Settings


@pytest.fixture
def bare_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Settings with every API key removed, ignoring any local .env file."""
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    return Settings(
        _env_file=None,
        openai_api_key=None,
        anthropic_api_key=None,
        google_api_key=None,
        groq_api_key=None,
    )
