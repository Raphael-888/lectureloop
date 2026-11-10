"""Explain a concept the student got wrong, with a citation that is checked against the slides."""

from __future__ import annotations

from app.agent.llm import UNTRUSTED, Asker, LLMError
from app.agent.search import best_line, verify_quote
from app.models import Explanation, QuestionItem
from app.schemas import Concept

SYSTEM = f"""TASK: explain
You are a patient tutor. A student got a question on one concept wrong. {UNTRUSTED}

Write a short explanation (3-5 sentences, plain English) that:
1. names the specific misunderstanding their answer shows, without being harsh;
2. explains the concept correctly, using ONLY what the slides in "slides" say;
3. does not reveal which option letter was correct, because they will be re-tested.

Then cite the one slide that best supports your explanation: "page" must be a page number from
"slides", and "quote" must be copied character for character from that page (one sentence or line,
at most 200 characters). Never invent a quote.

Reply with JSON only:
{{"explanation": "...", "page": 1, "quote": "..."}}"""


def explain(
    asker: Asker, concept: Concept, item: QuestionItem | None, student_answer: str, chunks: list[dict]
) -> Explanation:
    """`chunks` are search_slides results. The citation is always verified or rebuilt from them."""
    query = f"{concept.name} {concept.summary}"
    correct_answer = ""
    if item and item.type == "multiple_choice":
        correct_answer = next((o[3:] for o in item.options or [] if o[0] == item.answer), "")
    elif item:
        correct_answer = item.reference
    payload = {
        "concept": {"name": concept.name, "summary": concept.summary},
        "question": item.prompt if item else "",
        "options": [o[3:] for o in (item.options or [])] if item else [],
        "correct_answer": correct_answer,
        "student_answer": student_answer[:2000],
        "slides": [{"page": c["page"], "text": c["text"]} for c in chunks],
    }
    try:
        data = asker.ask("explain", SYSTEM, payload)
        text = data.get("explanation")
        if not isinstance(text, str) or not text.strip():
            raise LLMError("explain: empty explanation")
    except LLMError:
        return Explanation(concept_id=concept.id, text=concept.summary, citation=best_line(chunks, query))
    citation = verify_quote(chunks, data.get("page"), data.get("quote")) or best_line(
        chunks, f"{query} {text}"
    )
    return Explanation(concept_id=concept.id, text=text.strip()[:1500], citation=citation)
