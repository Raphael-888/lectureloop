"""Summaries shown before a quiz: the whole lecture (overview page) or the selected concepts.

Both are built from the slides and the concept graph. With a model the text is written for the
student; without one it is composed from C's concept summaries, so the pages always render.
"""

from __future__ import annotations

from app.agent.llm import UNTRUSTED, Asker, LLMError
from app.agent.search import MAX_CHUNK_CHARS
from app.models import Lecture
from app.schemas import Concept

SYSTEM = f"""TASK: summarize
You write a short review summary for a university student who has already attended the lecture
and now wants to revise the concepts in "concepts". {UNTRUSTED}

Write Markdown: one short paragraph (2-4 sentences) that ties the concepts together, then one
bullet per concept: "**Name** (p. X): one or two sentences on the essential idea", in the order
given. Use ONLY what "slides" say. No headings, no questions, no advice.

Reply with JSON only:
{{"summary_markdown": "..."}}"""

MAX_SLIDES = 12


def fallback(concepts: list[Concept], intro: str = "") -> str:
    lines = [intro, ""] if intro else []
    for c in concepts:
        lines.append(f"- **{c.name}** (p. {', '.join(map(str, c.pages))}): {c.summary}")
    return "\n".join(lines).strip()


def summarize(asker: Asker, lecture: Lecture, concepts: list[Concept]) -> str:
    """Markdown summary of `concepts`, written by the model or composed from the graph."""
    if not concepts:
        return ""
    wanted = sorted({p for c in concepts for p in c.pages})[:MAX_SLIDES]
    payload = {
        "lecture": lecture.title or lecture.filename,
        "concepts": [{"name": c.name, "summary": c.summary, "pages": c.pages} for c in concepts],
        "slides": [
            {"page": p.page, "text": p.text[:MAX_CHUNK_CHARS]} for p in lecture.pages if p.page in wanted
        ],
    }
    try:
        data = asker.ask("summarize", SYSTEM, payload)
        text = data.get("summary_markdown")
        if not isinstance(text, str) or len(text.strip()) < 20:
            raise LLMError("summarize: empty summary")
        return text.strip()[:4000]
    except LLMError:
        names = ", ".join(c.name for c in concepts[:-1])
        last = concepts[-1].name
        intro = (
            f"You are reviewing {len(concepts)} concepts: {names} and {last}."
            if len(concepts) > 1
            else f"You are reviewing one concept: {last}."
        )
        return fallback(concepts, intro)
