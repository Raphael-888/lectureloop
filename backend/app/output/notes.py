"""Personalised notes and flashcards for one session, weakest concepts first.

Built from stored data only (concept summaries, the agent's explanations and
the questions the student missed), so this endpoint is fast and costs nothing.
"""

from __future__ import annotations

import csv
import io

from app.learner.bkt import MASTERY_THRESHOLD, label_for, params_for
from app.models import Flashcard, Lecture, NotesResponse, QuestionItem, Session

_ICON = {"mastered": "✅", "confused": "⚠️", "not_mastered": "❌", "untested": "⬜"}
_WORDS = {
    "mastered": "mastered",
    "confused": "shaky",
    "not_mastered": "not mastered",
    "untested": "not tested",
}


def weak_concepts(lecture: Lecture, session: Session) -> list[str]:
    """Answered wrong at least once, or tested and still below the mastery threshold."""
    weak = [
        c.id
        for c in lecture.concepts
        if c.id in session.wrong or (c.id in session.p and session.p[c.id] < MASTERY_THRESHOLD)
    ]
    return sorted(weak, key=lambda cid: session.p.get(cid, 0.0))


def _answer_of(item: QuestionItem) -> str:
    if item.type == "multiple_choice":
        correct = next((o[3:] for o in item.options or [] if o[0] == item.answer), "")
        return f"{correct} ({item.reference})" if item.reference and item.reference != correct else correct
    return item.reference


def build_notes(lecture: Lecture, session: Session) -> NotesResponse:
    prior = params_for()["prior"]
    weak = weak_concepts(lecture, session)
    by_id = {c.id: c for c in lecture.concepts}

    def status(cid: str) -> tuple[str, str]:
        p = session.p.get(cid, prior)
        label = label_for(p, tested=cid in session.p)
        return label, f"{_WORDS[label]}, {round(p * 100)}%" if cid in session.p else _WORDS[label]

    def pages(cid: str) -> str:
        return ", ".join(str(p) for p in by_id[cid].pages)

    mastered = sum(1 for c in lecture.concepts if session.p.get(c.id, 0.0) >= MASTERY_THRESHOLD)
    lines = [
        f"# {lecture.title or lecture.filename}: review notes",
        "",
        f"**{mastered} of {len(lecture.concepts)} concepts mastered** in {len(session.answers)} questions.",
        "",
    ]

    if weak:
        lines += ["## Review these first", ""]
        for cid in weak:
            concept = by_id[cid]
            lines += [f"### {concept.name} (slides p. {pages(cid)})", "", f"*Status: {status(cid)[1]}*", ""]
            for cause in session.root_causes:
                if cause.root == cid and cause.symptom != cid:
                    lines += [
                        f"> This was the gap behind your trouble with **{by_id[cause.symptom].name}**.",
                        "",
                    ]
            explanation = session.explanations.get(cid)
            lines += [explanation.text if explanation else concept.summary, ""]
            if explanation and explanation.citation:
                lines += [f"> Slide p. {explanation.citation.page}: “{explanation.citation.quote}”", ""]

    lines += ["## All concepts", ""]
    for concept in lecture.concepts:
        label, _ = status(concept.id)
        lines.append(f"- {_ICON[label]} **{concept.name}** (p. {pages(concept.id)}): {concept.summary}")

    cards: list[Flashcard] = []
    for cid in weak:  # the exact questions the student missed
        item = session.issued.get(session.last_wrong.get(cid, ""))
        if item:
            cards.append(
                Flashcard(
                    front=item.prompt,
                    back=_answer_of(item),
                    concept_id=cid,
                    page=item.page or by_id[cid].pages[0],
                )
            )
    ordered = weak + [c.id for c in lecture.concepts if c.id not in weak]
    for cid in ordered:
        concept = by_id[cid]
        cards.append(
            Flashcard(
                front=f"Explain: {concept.name}", back=concept.summary, concept_id=cid, page=concept.pages[0]
            )
        )

    return NotesResponse(summary_markdown="\n".join(lines), weak_concepts=weak, flashcards=cards)


def flashcards_csv(notes: NotesResponse) -> str:
    """Two columns (front, back), no header: Anki's File > Import reads this directly."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    for card in notes.flashcards:
        writer.writerow([card.front, f"{card.back} (slide p. {card.page})"])
    return out.getvalue()
