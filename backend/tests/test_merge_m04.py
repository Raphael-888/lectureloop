import json
import re
from pathlib import Path

import pytest

from app.retrieval.merge import merge
from app.retrieval.pdf_parser import Page, parse_pdf

FIXTURES = Path(__file__).parent / "fixtures" / "lectures"
PDF_PATH = FIXTURES / "cs3151_m04.pdf"
VISION_PATH = FIXTURES / "cs3151_m04.vision.json"

pytestmark = pytest.mark.skipif(
    not (PDF_PATH.exists() and VISION_PATH.exists()),
    reason="M04 fixture files are not present locally",
)


@pytest.fixture(scope="module")
def records():
    pages = parse_pdf(PDF_PATH)
    vision = json.loads(VISION_PATH.read_text(encoding="utf-8"))
    return merge(pages, vision)


def _page(records, number):
    return next(r for r in records if r.page == number)


def test_page_types(records):
    assert _page(records, 18).page_type == "blank"
    assert _page(records, 1).page_type == "title"
    assert _page(records, 2).page_type == "outcomes"
    assert _page(records, 34).page_type == "quiz"
    assert _page(records, 35).page_type == "outlook"
    assert _page(records, 36).page_type == "references"
    assert _page(records, 6).page_type == "content"


def test_page_6_has_empirical_risk_formula(records):
    assert any("\\hat{L}_n" in formula for formula in _page(records, 6).formulas)


def test_page_16_text_mentions_global_minimum(records):
    assert "any local minimum is a global minimum" in _page(records, 16).text


def test_no_rich_text_starts_with_a_bare_page_number(records):
    leading_number = re.compile(r"^\d+(\s|$)")
    offenders = [r.page for r in records if leading_number.match(r.rich_text)]
    assert offenders == []


def _vision(page, slide_no):
    elements = [{"type": "text", "order": 1, "content": str(slide_no)}] if slide_no is not None else []
    elements.append({"type": "heading", "order": 2, "content": "Title"})
    return {"pages": [{"page": page, "status": "success", "elements": elements}]}


@pytest.mark.parametrize(
    "text_layer, vision_no, expected",
    [
        (18, 19, 18),  # both found: the PDF text layer wins
        (None, 19, 19),  # text layer has none: fall back to the vision reading
        (18, None, 18),
        (None, None, None),
    ],
)
def test_slide_no_prefers_text_layer(text_layer, vision_no, expected):
    page = Page(page=19, slide_no=text_layer, title="Title", text="Title\nbody", needs_vision=False)
    assert merge([page], _vision(19, vision_no))[0].slide_no == expected


def test_slide_no_without_vision_comes_from_text_layer():
    page = Page(page=3, slide_no=2, title="Title", text="Title\nbody", needs_vision=False)
    assert merge([page], {"pages": []})[0].slide_no == 2
