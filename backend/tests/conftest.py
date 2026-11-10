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


# --- Phase 2 fixtures: tiny documents and fakes --------------------------------------
from pathlib import Path  # noqa: E402

from app.ingest.store import VectorStore  # noqa: E402
from langchain_core.embeddings import DeterministicFakeEmbedding  # noqa: E402
from qdrant_client import QdrantClient  # noqa: E402

SAMPLE_TEXT_EN = (
    "# 1. Warranty period\n"
    "The standard warranty period is 24 months from delivery. Power supplies have 36 months.\n"
    "# 2. Claims\n"
    "Report the defect within 14 days. An RMA number is issued within 2 working days.\n"
)
SAMPLE_TEXT_DE = (
    "# 1. Laufzeit\n"
    "Der Vertrag hat eine feste Laufzeit von 36 Monaten und verlängert sich um 12 Monate, "
    "wenn er nicht mit einer Frist von 6 Monaten gekündigt wird.\n"
)


@pytest.fixture
def txt_file(tmp_path: Path) -> Path:
    path = tmp_path / "warranty.txt"
    path.write_text(SAMPLE_TEXT_EN, encoding="utf-8")
    return path


@pytest.fixture
def docx_file(tmp_path: Path) -> Path:
    from docx import Document

    doc = Document()
    doc.add_heading("§ 7 Gewährleistung", level=1)
    doc.add_paragraph("Die Gewährleistungsfrist beträgt 24 Monate ab Wareneingang.")
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Zahlungsziel"
    table.cell(0, 1).text = "Konditionen"
    table.cell(1, 0).text = "14 Tage"
    table.cell(1, 1).text = "3 % Skonto"
    doc.add_heading("§ 8 Haftung", level=1)
    doc.add_paragraph("Deckungssumme mindestens 5 Millionen Euro je Schadensfall.")
    path = tmp_path / "vertrag.docx"
    doc.save(str(path))
    return path


@pytest.fixture
def pdf_file(tmp_path: Path) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    path = tmp_path / "manual.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    c.drawString(72, 800, "1. Technical data")
    c.drawString(72, 780, "Nominal pressure 280 bar. Peak pressure 350 bar.")
    c.showPage()
    c.drawString(72, 800, "2. Maintenance intervals")
    c.drawString(72, 780, "Replace the filters every 2000 operating hours or 12 months.")
    c.showPage()
    c.save()
    return path


@pytest.fixture
def fake_embeddings() -> DeterministicFakeEmbedding:
    return DeterministicFakeEmbedding(size=64)


@pytest.fixture
def test_settings(tmp_path: Path, bare_settings: Settings) -> Settings:
    """Settings pointing index files at a temp dir with small chunks."""
    return bare_settings.model_copy(
        update={
            "index_dir": tmp_path / "index",
            "chunk_size": 200,
            "chunk_overlap": 40,
            "embed_batch_size": 4,
        }
    )


@pytest.fixture
def memory_store(
    fake_embeddings: DeterministicFakeEmbedding, test_settings: Settings
) -> VectorStore:
    """A VectorStore backed by an in-memory Qdrant (no Docker needed)."""
    return VectorStore(
        fake_embeddings, client=QdrantClient(":memory:"), collection="test", settings=test_settings
    )
