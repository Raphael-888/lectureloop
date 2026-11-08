"""Merge the PDF text layer with the vision model's reading, one record per page.

The text layer is the source of truth for citations: the vision model's
transcription occasionally rewrites or fills in words, so `PageRecord.text`
must always come straight from the PDF and is never overwritten.
"""

from __future__ import annotations

from app.retrieval.page_types import classify_page_type
from app.retrieval.pdf_parser import Page
from app.retrieval.vision_merge import merge_page_elements
from app.schemas import PageRecord


def _first_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def merge(pages: list[Page], vision: dict) -> list[PageRecord]:
    vision_by_page = {
        entry["page"]: entry for entry in vision.get("pages", []) if entry.get("status") == "success"
    }

    records: list[PageRecord] = []

    for page in pages:
        vision_entry = vision_by_page.get(page.page)
        has_vision = vision_entry is not None

        if has_vision:
            content = merge_page_elements(vision_entry.get("elements", []))
            rich_text = content.rich_text
            title = content.title or _first_line(page.text)
            # the PDF text layer is exact; the vision reading is only a fallback
            slide_no = page.slide_no if page.slide_no is not None else content.slide_no
            formulas = content.formulas
            figures = content.figures
            uncertain = content.uncertain
        else:
            rich_text = page.text
            title = _first_line(page.text)
            slide_no = page.slide_no
            formulas = []
            figures = []
            uncertain = []

        page_type = classify_page_type(
            page_number=page.page,
            title=title,
            text=page.text,
            rich_text=rich_text,
        )

        records.append(
            PageRecord(
                page=page.page,
                slide_no=slide_no,
                title=title,
                page_type=page_type,
                text=page.text,
                rich_text=rich_text,
                formulas=formulas,
                figures=figures,
                uncertain=uncertain,
                has_vision=has_vision,
            )
        )

    return records
