"""Turn PDF, DOCX and TXT files into a uniform list of text segments.

Every segment carries the page number (PDF only) and the nearest heading above it,
so that later chunks can be cited as "document, page, section".
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from docx import Document as DocxDocument
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader

logger = logging.getLogger(__name__)

FileType = Literal["pdf", "docx", "txt"]
SUPPORTED_EXTENSIONS: dict[str, FileType] = {".pdf": "pdf", ".docx": "docx", ".txt": "txt"}

# "1. Title", "3.2 Title", "§ 7 Gewährleistung", "# Title" (markdown), "## Title"
_HEADING_RE = re.compile(r"^(?:#{1,3}\s+\S.*|§\s*\d+\s+\S.*|\d+\.(?:\d+\.?)*\s+[A-ZÄÖÜ].{2,80})$")
# footer our sample PDFs (and many real ones) print on every page
_FOOTER_RE = re.compile(r"^(?:Rheintal Antriebstechnik GmbH\s*)?Page \d+\s*$|^Seite \d+\s*$")


@dataclass
class Segment:
    """A run of text that belongs to one page and one section heading."""

    text: str
    page: int | None = None
    section: str | None = None


@dataclass
class ParsedDocument:
    """Result of parsing one file."""

    filename: str
    file_type: FileType
    segments: list[Segment] = field(default_factory=list)
    num_pages: int = 0

    @property
    def text(self) -> str:
        """Full text, used for language detection and tests."""
        return "\n".join(s.text for s in self.segments)


class UnsupportedFileTypeError(ValueError):
    """Raised for file extensions we cannot parse."""


def detect_file_type(path: Path) -> FileType:
    """Map a file extension to a supported type or raise UnsupportedFileTypeError."""
    file_type = SUPPORTED_EXTENSIONS.get(path.suffix.lower())
    if file_type is None:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{path.suffix}'. Supported: pdf, docx, txt."
        )
    return file_type


def is_heading(line: str) -> bool:
    """Return True if a line of text looks like a numbered or markdown heading."""
    line = line.strip()
    return bool(line) and len(line) <= 100 and bool(_HEADING_RE.match(line))


def clean_text(text: str) -> str:
    """Normalise whitespace: collapse spaces, drop empty lines and page footers."""
    lines = []
    for raw in text.splitlines():
        line = re.sub(r"[ \t ]+", " ", raw).strip()
        if not line or _FOOTER_RE.match(line):
            continue
        lines.append(line)
    return "\n".join(lines)


def _segments_from_lines(text: str, page: int | None, section: str | None) -> list[Segment]:
    """Split a block of lines into segments at heading lines, tracking the current section."""
    segments: list[Segment] = []
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            segments.append(Segment("\n".join(buffer), page=page, section=section))
            buffer.clear()

    for line in clean_text(text).splitlines():
        if is_heading(line):
            flush()
            section = line.lstrip("#").strip()
            buffer.append(line.lstrip("#").strip())
        else:
            buffer.append(line)
    flush()
    return segments


def parse_pdf(path: Path) -> ParsedDocument:
    """Extract text page by page with pypdf, detecting headings inside each page."""
    reader = PdfReader(str(path))
    doc = ParsedDocument(filename=path.name, file_type="pdf", num_pages=len(reader.pages))
    section: str | None = None
    for number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        page_segments = _segments_from_lines(text, page=number, section=section)
        if page_segments:
            section = page_segments[-1].section
        doc.segments.extend(page_segments)
    logger.debug("parsed %s: %d pages, %d segments", path.name, doc.num_pages, len(doc.segments))
    return doc


def _table_to_text(table: Table) -> str:
    """Render a DOCX table as pipe-separated rows so the values stay searchable."""
    rows = []
    for row in table.rows:
        cells = [re.sub(r"\s+", " ", c.text).strip() for c in row.cells]
        rows.append(" | ".join(cells))
    return "\n".join(rows)


def _iter_docx_blocks(document: DocxDocument) -> list[Paragraph | Table]:  # type: ignore[valid-type]
    """Yield paragraphs and tables in document order (python-docx keeps them separate)."""
    body = document.element.body
    blocks: list[Paragraph | Table] = []
    for child in body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            blocks.append(Paragraph(child, document))
        elif tag == "tbl":
            blocks.append(Table(child, document))
    return blocks


def parse_docx(path: Path) -> ParsedDocument:
    """Read a DOCX, using heading styles for sections and flattening tables to text."""
    document = DocxDocument(str(path))
    doc = ParsedDocument(filename=path.name, file_type="docx", num_pages=0)
    section: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            doc.segments.append(Segment("\n".join(buffer), page=None, section=section))
            buffer.clear()

    for block in _iter_docx_blocks(document):
        if isinstance(block, Table):
            buffer.append(_table_to_text(block))
            continue
        text = clean_text(block.text)
        if not text:
            continue
        style = (block.style.name or "") if block.style is not None else ""
        if style.startswith("Heading") or is_heading(text):
            flush()
            section = text
        buffer.append(text)
    flush()
    return doc


def parse_txt(path: Path) -> ParsedDocument:
    """Read a UTF-8 text file; markdown '#' lines and numbered lines become sections."""
    text = path.read_text(encoding="utf-8", errors="replace")
    doc = ParsedDocument(filename=path.name, file_type="txt", num_pages=0)
    doc.segments = _segments_from_lines(text, page=None, section=None)
    return doc


def parse_file(path: Path) -> ParsedDocument:
    """Parse any supported file into a ParsedDocument."""
    file_type = detect_file_type(path)
    if file_type == "pdf":
        return parse_pdf(path)
    if file_type == "docx":
        return parse_docx(path)
    return parse_txt(path)
