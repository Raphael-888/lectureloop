"""Text-layer parsing for lecture PDFs (no vision model involved)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

_LIGATURES = {
    "ﬀ": "ff",
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
}

MIN_CHARS = 40  # less than this after cleaning -> content is probably visual

# Lines that are export noise, not slide content.
_NOISE = [
    re.compile(r"^\d{4}-\d{2}-\d{2}, \d{1,2}:\d{2}\s*[AP]M"),  # browser print timestamp
    re.compile(r"^Page \d+ of \d+"),  # browser print footer
    re.compile(r"^https?://\S+$"),
    re.compile(r"^▶ Code$"),  # collapsed code-cell marker
]
_NUMERIC_LINE = re.compile(r"^[\d\s.,\-+e]+$")  # plot axis ticks like "0.2" or "0 2 4 6"


@dataclass
class Page:
    page: int  # PDF page, 1-based
    slide_no: int | None  # number printed on the slide, if found
    title: str  # first line after cleaning
    text: str
    needs_vision: bool  # text is (almost) empty -> look at the image instead


def clean_page_text(raw: str) -> tuple[str, int | None]:
    """Remove print headers, plot ticks and the trailing slide number."""
    for ligature, replacement in _LIGATURES.items():
        raw = raw.replace(ligature, replacement)

    lines = [ln.strip() for ln in raw.splitlines()]
    lines = [ln for ln in lines if ln and not any(p.match(ln) for p in _NOISE)]

    slide_no = None
    if lines and lines[-1].isdigit():
        slide_no = int(lines.pop())

    lines = [ln for ln in lines if not _NUMERIC_LINE.match(ln)]
    return "\n".join(lines), slide_no


def parse_pdf(pdf_path: str | Path) -> list[Page]:
    """Extract and clean the text layer of every page, 1-indexed."""

    doc = pymupdf.open(pdf_path)
    try:
        pages = []
        for index in range(len(doc)):
            text, slide_no = clean_page_text(doc[index].get_text())
            title = text.split("\n", 1)[0] if text else ""
            pages.append(
                Page(
                    page=index + 1,
                    slide_no=slide_no,
                    title=title,
                    text=text,
                    needs_vision=len(text) < MIN_CHARS,
                )
            )
        return pages
    finally:
        doc.close()


PAGE_IMAGE_WIDTH = 1200  # px; wide enough to read a slide in the review page's PDF pane


def render_page_images(pdf_path: str | Path, out_dir: Path, width: int = PAGE_IMAGE_WIDTH, max_pages: int | None = None) -> int:
    """Render each page to out_dir/<page>.png (1-indexed) so the review page can show the slides
    as they look in the PDF. Returns the number of pages written."""

    out_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    try:
        count = len(doc) if max_pages is None else min(len(doc), max_pages)
        for index in range(count):
            page = doc[index]
            zoom = width / page.rect.width
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
            pixmap.save(out_dir / f"{index + 1}.png")
        return count
    finally:
        doc.close()
