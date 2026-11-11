"""The tutor chat: answers questions about the selected concepts and takes quiz instructions.

Two jobs in one call, because the product has one chat box and no settings buttons:
1. answer the student's question from the slides (with a page reference);
2. if the message asks to change how they are quizzed ("make it harder", "short answer
   instead"), update the session's preferences. Chatting never grades anything and never
   touches mastery (D's REVIEW_INTEGRATION.md).
"""

from __future__ import annotations

import re

from app.agent.llm import UNTRUSTED, Asker, LLMError
from app.agent.search import search_pages
from app.models import ChatMessage, ChatResponse, Lecture, Preferences, Session
from app.schemas import Concept

SYSTEM = f"""TASK: chat
You are the tutor of LectureLoop. A student is reviewing the concepts listed in "concepts" from one
lecture and sends you a message. {UNTRUSTED}

Do two things:
1. "reply": answer the message in 2-5 plain sentences for the student, using ONLY what "slides"
   say. Refer to slide pages as "p. 12". If the slides do not cover it, say so briefly.
   If the message is an instruction about the quiz rather than a question, confirm what you
   will change in one sentence.
2. Quiz settings. If the student asks to change the kind of questions, set:
   - "question_type": "multiple_choice" or "short_answer" (open questions answered in their own
     words, which also covers "calculation", "proof", "explain" or "written" questions),
     or null to leave it unchanged;
   - "difficulty": "easier", "same" or "harder", or null to leave it unchanged.
   Set both to null when the message is only a question about the material.

Reply with JSON only:
{{"reply": "...", "question_type": null, "difficulty": null}}"""

_HARDER = re.compile(r"\b(harder|more difficult|challeng|tough|advanced|calculation|apply|proof)", re.I)
_EASIER = re.compile(r"\b(easier|simpler|simple|basic|gentle|beginner|too hard)", re.I)
_MCQ = re.compile(r"\b(multiple[- ]choice|mcq|options|choices|a/b/c/d)", re.I)
_OPEN = re.compile(r"\b(short[- ]answer|open[- ]ended|free[- ]text|written|in my own words|essay)\b", re.I)
_HISTORY = 6  # earlier messages sent to the model for context


def _rules(message: str) -> tuple[str | None, str | None]:
    """Preference changes read from the message without a model (also the offline stand-in)."""
    qtype = "multiple_choice" if _MCQ.search(message) else "short_answer" if _OPEN.search(message) else None
    level = "harder" if _HARDER.search(message) else "easier" if _EASIER.search(message) else None
    return qtype, level


def _fallback_reply(message: str, concepts: list[Concept], chunks: list[dict], changes: list[str]) -> str:
    if changes:
        return "Got it. " + " ".join(changes)
    if chunks:
        top = chunks[0]
        line = next((ln.strip() for ln in top["text"].splitlines() if len(ln.strip()) > 20), "")
        if line:
            return f"The slides cover this on p. {top['page']}: “{line[:200]}”"
        return f"Have a look at p. {top['page']} ({top['title'] or 'that slide'})."
    if concepts:
        c = concepts[0]
        return f"{c.name}: {c.summary} (p. {', '.join(map(str, c.pages))})"
    return "I could not find that in the slides. Try asking about one of the selected concepts."


def _describe(prefs: Preferences, before: Preferences) -> list[str]:
    out = []
    if prefs.question_type != before.question_type:
        kind = {"multiple_choice": "multiple-choice", "short_answer": "open (short-answer)"}
        out.append(
            f"From the next question on you'll get {kind[prefs.question_type]} questions."
            if prefs.question_type
            else "I'll choose the question type again."
        )
    if prefs.difficulty != before.difficulty:
        out.append(
            {
                "harder": "The next questions will be harder: applying the idea, not just recalling it.",
                "easier": "The next questions will be easier and more about recall.",
                "same": "Back to the normal difficulty.",
            }[prefs.difficulty]
        )
    return out


def chat(asker: Asker, lecture: Lecture, session: Session, message: str) -> ChatResponse:
    message = " ".join(message.split())[:2000]
    scope = [c for c in lecture.concepts if not session.targets or c.id in session.targets]
    query = f"{message} " + " ".join(c.name for c in scope)
    chunks = search_pages(lecture.pages, query, k=3, prefer=[p for c in scope for p in c.pages])
    before = session.preferences.model_copy()
    prefs = session.preferences

    payload = {
        "concepts": [{"name": c.name, "summary": c.summary, "pages": c.pages} for c in scope],
        "current_settings": prefs.model_dump(),
        "history": [{"role": m.role, "text": m.text[:500]} for m in session.chat[-_HISTORY:]],
        "message": message,
        "slides": [{"page": c["page"], "text": c["text"]} for c in chunks],
    }
    reply = ""
    qtype = level = None
    try:
        data = asker.ask("chat", SYSTEM, payload)
        text = data.get("reply")
        if not isinstance(text, str) or not text.strip():
            raise LLMError("chat: empty reply")
        reply = text.strip()[:1500]
        qtype = data.get("question_type") if data.get("question_type") in ("multiple_choice", "short_answer") else None
        level = data.get("difficulty") if data.get("difficulty") in ("easier", "same", "harder") else None
    except LLMError:
        qtype, level = _rules(message)

    if qtype:
        prefs.question_type = qtype
    if level:
        prefs.difficulty = level
    changed = [k for k in ("question_type", "difficulty") if getattr(prefs, k) != getattr(before, k)]
    if not reply:
        reply = _fallback_reply(message, scope, chunks, _describe(prefs, before))

    session.chat.append(ChatMessage(role="student", text=message))
    session.chat.append(ChatMessage(role="tutor", text=reply))
    if chunks:
        pages = ", ".join(str(c["page"]) for c in chunks)
        session.add_trace("search_slides", "Find slide evidence for the student's question", f"Top pages: {pages}")
    summary = "Answered from the slides" if not changed else "Updated quiz settings: " + ", ".join(
        f"{k}={getattr(prefs, k)}" for k in changed
    )
    session.add_trace("chat", f'Student wrote: "{message[:80]}"', summary)
    return ChatResponse(reply=reply, preferences=prefs, changed=changed)
