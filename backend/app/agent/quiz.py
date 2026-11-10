"""generate_quiz: build a question bank per concept, and pick the next question for a session."""

from __future__ import annotations

import random
import re
import secrets
from concurrent.futures import ThreadPoolExecutor

from app.agent.llm import UNTRUSTED, Asker, LLMError
from app.agent.policy import coverage_order
from app.agent.search import MAX_CHUNK_CHARS, tokenize
from app.models import Lecture, QuestionItem, Session
from app.schemas import Concept
from app.store import Store

BATCH = 3  # concepts per model call
LETTERS = "ABCD"

SYSTEM = f"""TASK: quiz
You write quiz questions for ONE university lecture. {UNTRUSTED}

For EACH concept in "concepts" write exactly 2 multiple_choice questions and 1 short_answer question.
Rules:
1. Test understanding of that concept only, using what the slides in "slides" actually teach.
   Do not test prerequisites or later concepts, and do not ask about slide numbers or wording.
2. The questions for one concept must probe different aspects of it.
3. multiple_choice: exactly 4 options, exactly one correct. Distractors are plausible mistakes a
   confused student would make. No "all of the above" or "none of the above". No option letters.
4. short_answer: answerable in 1-3 sentences. Give a model answer and 2-4 key points.
5. "page": the slide page (a number from that concept's "pages") that best supports the answer.

Reply with JSON only:
{{"questions": [
  {{"concept_id": "...", "type": "multiple_choice", "prompt": "...", "options": ["...", "...", "...", "..."],
    "answer_index": 0, "explanation": "why that option is right, one sentence", "page": 1}},
  {{"concept_id": "...", "type": "short_answer", "prompt": "...", "reference_answer": "...",
    "key_points": ["...", "..."], "page": 1}}
]}}"""


def _new_id() -> str:
    return f"q_{secrets.token_hex(6)}"


def _text(value: object, limit: int) -> str:
    return value.strip()[:limit] if isinstance(value, str) else ""


def _to_item(raw: object, concepts: dict[str, Concept]) -> QuestionItem | None:
    """Validate one model-written question. Anything malformed is dropped, not repaired."""
    if not isinstance(raw, dict) or raw.get("concept_id") not in concepts:
        return None
    concept = concepts[raw["concept_id"]]
    prompt = _text(raw.get("prompt"), 600)
    if not prompt:
        return None
    page = raw.get("page")
    page = page if isinstance(page, int) and page in concept.pages else concept.pages[0]

    if raw.get("type") == "multiple_choice":
        options = raw.get("options")
        index = raw.get("answer_index")
        if not isinstance(options, list) or len(options) != 4 or index not in (0, 1, 2, 3):
            return None
        options = [re.sub(r"^\s*[A-Da-d][.)]\s+", "", _text(o, 300)) for o in options]
        if not all(options) or len({o.lower() for o in options}) != 4:
            return None
        order = list(range(4))
        random.Random(prompt).shuffle(order)  # the model tends to put the answer first
        return QuestionItem(
            id=_new_id(),
            concept_id=concept.id,
            type="multiple_choice",
            prompt=prompt,
            options=[f"{LETTERS[i]}. {options[src]}" for i, src in enumerate(order)],
            answer=LETTERS[order.index(index)],
            reference=_text(raw.get("explanation"), 500) or options[index],
            page=page,
        )

    if raw.get("type") == "short_answer":
        reference = _text(raw.get("reference_answer"), 800)
        if not reference:
            return None
        points = raw.get("key_points") if isinstance(raw.get("key_points"), list) else []
        return QuestionItem(
            id=_new_id(),
            concept_id=concept.id,
            type="short_answer",
            prompt=prompt,
            reference=reference,
            key_points=[p for p in (_text(p, 200) for p in points[:5]) if p],
            page=page,
        )
    return None


def generate(asker: Asker, lecture: Lecture, concepts: list[Concept]) -> list[QuestionItem]:
    """One model call for a few concepts. Raises LLMError if the call fails."""
    wanted = sorted({p for c in concepts for p in c.pages})
    payload = {
        "concepts": [c.model_dump() for c in concepts],
        "slides": [
            {"page": p.page, "text": p.text[:MAX_CHUNK_CHARS]} for p in lecture.pages if p.page in wanted
        ],
        "other_concepts_in_lecture": [c.name for c in lecture.concepts if c not in concepts],
    }
    data = asker.ask("generate_quiz", SYSTEM, payload)
    by_id = {c.id: c for c in concepts}
    raw_items = data.get("questions") if isinstance(data.get("questions"), list) else []
    return [item for item in (_to_item(r, by_id) for r in raw_items) if item is not None]


def prefill_bank(store: Store, lecture: Lecture, asker: Asker) -> int:
    """Generate questions for every concept, a few concepts per call, in parallel.

    Batches follow the order sessions ask in, so the first questions are ready first.
    """
    concepts = [lecture.concept(cid) for cid in coverage_order(lecture.concepts)]
    batches = [concepts[i : i + BATCH] for i in range(0, len(concepts), BATCH)]

    def run(batch: list[Concept]) -> int:
        try:
            items = generate(asker, lecture, batch)
        except LLMError:
            return 0  # pick() generates on demand for concepts that are still empty
        store.add_questions(lecture.id, items)
        return len(items)

    with ThreadPoolExecutor(max_workers=4) as pool:
        return sum(pool.map(run, batches))


def _fallback(concept: Concept) -> QuestionItem:
    """Last resort when the bank is empty and the model is unavailable."""
    return QuestionItem(
        id=_new_id(),
        concept_id=concept.id,
        type="short_answer",
        prompt=f"In your own words, explain this idea from the lecture: {concept.name}.",
        reference=concept.summary,
        key_points=sorted(set(tokenize(concept.summary)), key=len, reverse=True)[:4],
        page=concept.pages[0],
    )


def pick(
    store: Store, lecture: Lecture, session: Session, concept_id: str, asker: Asker, short_answer: bool = True
) -> QuestionItem:
    """Next unseen question on a concept: multiple choice first, short answer to confirm."""
    concept = lecture.concept(concept_id)

    def unseen() -> list[QuestionItem]:
        seen_prompts = {q.prompt for q in session.issued.values()}
        return [
            q
            for q in store.list_questions(lecture.id, concept_id)
            if q.id not in session.issued
            and q.prompt not in seen_prompts
            and (short_answer or q.type == "multiple_choice")
        ]

    candidates = unseen()
    if not candidates:
        try:
            store.add_questions(lecture.id, generate(asker, lecture, [concept]))
        except LLMError:
            pass
        candidates = unseen()
    if not candidates:
        return _fallback(concept)

    first_try = session.attempts.get(concept_id, 0) == 0
    preferred = "multiple_choice" if first_try else "short_answer"
    candidates.sort(key=lambda q: q.type != preferred)  # stable: keeps bank order within a type
    return candidates[0]
