"""Parser tests on tiny generated fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.ingest.parsers import (
    UnsupportedFileTypeError,
    clean_text,
    is_heading,
    parse_docx,
    parse_file,
    parse_pdf,
    parse_txt,
)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("1. General information", True),
        ("3.2 Tightening torques", True),
        ("§ 7 Gewährleistung", True),
        ("## 5. Vacation", True),
        ("The pump weighs 38 kg.", False),
        ("280 bar", False),
        ("", False),
    ],
)
def test_is_heading(line: str, expected: bool) -> None:
    assert is_heading(line) is expected


def test_clean_text_drops_footers_and_blank_lines() -> None:
    raw = "Rheintal Antriebstechnik GmbH Page 2\n\n  Hello   world \n\nSeite 3\n"
    assert clean_text(raw) == "Hello world"


def test_parse_txt_sections(txt_file: Path) -> None:
    doc = parse_txt(txt_file)
    assert doc.file_type == "txt"
    assert [s.section for s in doc.segments] == ["1. Warranty period", "2. Claims"]
    assert "24 months" in doc.segments[0].text
    assert doc.segments[0].page is None


def test_parse_docx_headings_and_tables(docx_file: Path) -> None:
    doc = parse_docx(docx_file)
    sections = [s.section for s in doc.segments]
    assert sections == ["§ 7 Gewährleistung", "§ 8 Haftung"]
    assert "14 Tage | 3 % Skonto" in doc.segments[0].text
    assert "5 Millionen" in doc.segments[1].text


def test_parse_pdf_pages(pdf_file: Path) -> None:
    doc = parse_pdf(pdf_file)
    assert doc.num_pages == 2
    pages = sorted({s.page for s in doc.segments})
    assert pages == [1, 2]
    second = [s for s in doc.segments if s.page == 2][0]
    assert second.section == "2. Maintenance intervals"
    assert "2000 operating hours" in second.text


def test_parse_file_dispatch_and_unsupported(txt_file: Path, tmp_path: Path) -> None:
    assert parse_file(txt_file).file_type == "txt"
    bad = tmp_path / "image.png"
    bad.write_bytes(b"\x89PNG")
    with pytest.raises(UnsupportedFileTypeError):
        parse_file(bad)
