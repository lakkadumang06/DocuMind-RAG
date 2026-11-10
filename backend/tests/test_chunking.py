"""Chunking tests: sizes, overlap, metadata and language detection."""

from __future__ import annotations

import pytest
from app.ingest.chunking import chunk_document, detect_language
from app.ingest.parsers import ParsedDocument, Segment


def _doc() -> ParsedDocument:
    long_en = " ".join(f"Sentence number {i} about hydraulic pumps and filters." for i in range(30))
    return ParsedDocument(
        filename="manual.pdf",
        file_type="pdf",
        num_pages=2,
        segments=[
            Segment("1. Intro\nShort intro text about the pump.", page=1, section="1. Intro"),
            Segment("2. Details\n" + long_en, page=2, section="2. Details"),
        ],
    )


def test_chunks_respect_size_and_keep_metadata() -> None:
    chunks = chunk_document(_doc(), document_id="abc", chunk_size=300, chunk_overlap=50)
    assert len(chunks) > 3
    for c in chunks:
        # section prefix may add a few chars on top of chunk_size
        assert len(c.text) <= 300 + len("2. Details\n")
        assert c.document_id == "abc"
        assert c.id == f"abc:{c.chunk_index}"
        assert c.page in (1, 2)
    assert chunks[0].section == "1. Intro" and chunks[0].page == 1
    assert all(c.section == "2. Details" for c in chunks[1:])
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_chunks_overlap() -> None:
    chunks = chunk_document(_doc(), document_id="abc", chunk_size=300, chunk_overlap=80)
    a, b = chunks[1].text, chunks[2].text
    # the tail of chunk 1 should re-appear at the start of chunk 2
    tail = a[-40:].split(" ", 1)[-1]
    assert tail.split(" ")[0] in b


def test_section_is_prepended_once() -> None:
    chunks = chunk_document(_doc(), document_id="abc", chunk_size=300, chunk_overlap=50)
    assert chunks[1].text.startswith("2. Details\n")
    assert chunks[1].text.count("2. Details") == 1


def test_overlap_must_be_smaller_than_size() -> None:
    with pytest.raises(ValueError):
        chunk_document(_doc(), document_id="x", chunk_size=100, chunk_overlap=100)


def test_detect_language() -> None:
    assert detect_language("The standard warranty period is 24 months from delivery date.") == "en"
    assert (
        detect_language("Die Gewährleistungsfrist beträgt 24 Monate ab Wareneingang beim Kunden.")
        == "de"
    )
    assert detect_language("short", fallback="de") == "de"
    assert detect_language("x" * 100, fallback="de") == "de"
