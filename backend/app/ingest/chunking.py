"""Split parsed documents into overlapping chunks that keep page and section metadata."""

from __future__ import annotations

import logging
from itertools import groupby

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langdetect import DetectorFactory, LangDetectException, detect

from app.ingest.parsers import ParsedDocument, Segment
from app.schemas import Chunk

logger = logging.getLogger(__name__)

DetectorFactory.seed = 0  # make langdetect deterministic
SUPPORTED_LANGUAGES = {"en", "de"}
MIN_CHARS_FOR_DETECTION = 60


def detect_language(text: str, fallback: str = "en") -> str:
    """Return 'en' or 'de' for the text; anything else or too-short text yields the fallback."""
    if len(text) < MIN_CHARS_FOR_DETECTION:
        return fallback
    try:
        lang = detect(text)
    except LangDetectException:
        return fallback
    return lang if lang in SUPPORTED_LANGUAGES else fallback


def _splitter(chunk_size: int, chunk_overlap: int) -> RecursiveCharacterTextSplitter:
    # Paragraphs first, then lines, then sentences, then words.
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", "; ", ", ", " ", ""],
        length_function=len,
    )


def _group_segments(segments: list[Segment]) -> list[Segment]:
    """Merge consecutive segments with the same page and section into one block."""
    grouped: list[Segment] = []
    for (page, section), items in groupby(segments, key=lambda s: (s.page, s.section)):
        text = "\n".join(s.text for s in items)
        grouped.append(Segment(text=text, page=page, section=section))
    return grouped


def chunk_document(
    doc: ParsedDocument,
    document_id: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Chunk]:
    """Chunk a parsed document.

    Segments are grouped by (page, section) so no chunk spans two sections or pages;
    each group is then split recursively by paragraph, line and sentence boundaries.
    Section headings are prepended to chunks that do not start with them, which helps
    both BM25 and embeddings understand the context of a table row like "Weekly | ...".
    """
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")
    splitter = _splitter(chunk_size, chunk_overlap)
    doc_language = detect_language(doc.text)

    chunks: list[Chunk] = []
    for block in _group_segments(doc.segments):
        for piece in splitter.split_text(block.text):
            text = piece.strip()
            if not text or text == block.section:
                continue
            if block.section and not text.startswith(block.section):
                text = f"{block.section}\n{text}"
            index = len(chunks)
            chunks.append(
                Chunk(
                    id=f"{document_id}:{index}",
                    document_id=document_id,
                    document_name=doc.filename,
                    chunk_index=index,
                    text=text,
                    page=block.page,
                    section=block.section,
                    language=detect_language(text, fallback=doc_language),
                )
            )
    logger.info(
        "%s: %d chunks (size=%d, overlap=%d)", doc.filename, len(chunks), chunk_size, chunk_overlap
    )
    return chunks
