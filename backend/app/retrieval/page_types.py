"""Rule-based page-type classification (no model call)."""

from __future__ import annotations

from app.schemas import PageType

_OUTCOMES_KEYWORDS = ("outcomes", "learning objectives")
_QUIZ_KEYWORDS = ("quick check", "quiz", "exercise")
_OUTLOOK_KEYWORDS = ("looking ahead", "next steps")
_REFERENCES_KEYWORDS = ("references", "bibliography")


def classify_page_type(
    page_number: int,
    title: str | None,
    text: str,
    rich_text: str,
) -> PageType:
    if not text.strip() and not rich_text.strip():
        return "blank"

    if page_number == 1:
        return "title"

    title_lower = (title or "").lower()

    if any(keyword in title_lower for keyword in _OUTCOMES_KEYWORDS):
        return "outcomes"

    if any(keyword in title_lower for keyword in _QUIZ_KEYWORDS):
        return "quiz"

    if any(keyword in title_lower for keyword in _OUTLOOK_KEYWORDS):
        return "outlook"

    if any(keyword in title_lower for keyword in _REFERENCES_KEYWORDS):
        return "references"

    return "content"
