"""Models owned by B: API bodies (docs/api-contract.md) and stored lecture/session state.

C's pipeline models (Concept, ConceptGraph, PageRecord) stay in app/schemas.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas import Concept

QuestionType = Literal["multiple_choice", "short_answer"]
MasteryLabel = Literal["mastered", "confused", "not_mastered", "untested"]
NextAction = Literal["next_question", "explain", "test_prerequisite", "done"]
LectureStatus = Literal["processing", "ready", "failed"]


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------- stored ----------


class SlidePage(BaseModel):
    page: int  # PDF page, 1-based
    title: str = ""
    page_type: str = "content"
    text: str = ""  # exact PDF text layer: the only source for citation quotes


class Lecture(BaseModel):
    id: str
    filename: str
    title: str = ""
    status: LectureStatus = "processing"
    error: str | None = None
    created_at: str = Field(default_factory=now_iso)
    pages: list[SlidePage] = Field(default_factory=list)
    concepts: list[Concept] = Field(default_factory=list)
    overview: str = ""  # Markdown summary of the whole lecture (unused by the UI since Nov 12)
    bookmarks: list["Bookmark"] = Field(default_factory=list)  # the student's saved questions
    timings: dict[str, float] = Field(default_factory=dict)  # seconds per pipeline stage

    def concept(self, concept_id: str) -> Concept:
        for c in self.concepts:
            if c.id == concept_id:
                return c
        raise KeyError(concept_id)


class QuestionItem(BaseModel):
    """A question with its answer key. Never send this to the client; use public()."""

    id: str
    concept_id: str
    type: QuestionType
    prompt: str
    options: list[str] | None = None  # "A. ..." to "D. ..."
    answer: str | None = None  # correct option letter (multiple_choice)
    reference: str = ""  # why the answer is right / model answer (short_answer)
    key_points: list[str] = Field(default_factory=list)
    page: int | None = None
    difficulty: Literal["easier", "same", "harder"] = "same"  # the level it was generated at

    def public(self) -> Question:
        return Question(
            id=self.id, concept_id=self.concept_id, type=self.type, prompt=self.prompt, options=self.options
        )


class Citation(BaseModel):
    page: int
    quote: str


class Explanation(BaseModel):
    concept_id: str
    text: str
    citation: Citation | None = None


class TraceEvent(BaseModel):
    step: int
    time: str
    tool: str
    reason: str
    summary: str


class RootCause(BaseModel):
    symptom: str  # concept the student first got wrong
    root: str  # deepest concept with no unresolved prerequisite (a hypothesis, see D's README)
    step: int


class Preferences(BaseModel):
    """How the student wants to be quizzed; set through the tutor chat, never by a graded answer."""

    question_type: QuestionType | None = None  # None = the agent decides (multiple choice first)
    difficulty: Literal["easier", "same", "harder"] = "same"


class ChatMessage(BaseModel):
    role: Literal["student", "tutor"]
    text: str
    time: str = Field(default_factory=now_iso)


class Session(BaseModel):
    id: str
    lecture_id: str
    created_at: str = Field(default_factory=now_iso)
    targets: list[str] = Field(default_factory=list)  # selected concept ids; empty = whole lecture
    scope_summary: str = ""  # tutor's summary of the selected concepts, shown before the quiz
    preferences: Preferences = Field(default_factory=Preferences)
    chat: list[ChatMessage] = Field(default_factory=list)
    p: dict[str, float] = Field(default_factory=dict)  # tested concepts only
    attempts: dict[str, int] = Field(default_factory=dict)
    wrong: list[str] = Field(default_factory=list)  # concepts answered wrong at least once
    last_wrong: dict[str, str] = Field(default_factory=dict)  # concept -> question id
    stack: list[str] = Field(default_factory=list)  # concepts waiting on a prerequisite check
    issued: dict[str, QuestionItem] = Field(default_factory=dict)
    current_question: str | None = None  # the only question that may be answered next
    answers: dict[str, str] = Field(default_factory=dict)  # question id -> student answer
    responses: dict[str, dict] = Field(default_factory=dict)  # question id -> AnswerResponse
    explanations: dict[str, Explanation] = Field(default_factory=dict)
    root_causes: list[RootCause] = Field(default_factory=list)
    trace: list[TraceEvent] = Field(default_factory=list)
    done: bool = False

    def add_trace(self, tool: str, reason: str, summary: str) -> TraceEvent:
        event = TraceEvent(
            step=len(self.trace) + 1, time=now_iso(), tool=tool, reason=reason[:300], summary=summary[:300]
        )
        self.trace.append(event)
        return event


# ---------- API bodies ----------


class Question(BaseModel):
    id: str
    concept_id: str
    type: QuestionType
    prompt: str
    options: list[str] | None = None


class Mastery(BaseModel):
    concept_id: str
    p_mastery: float
    label: MasteryLabel


class UploadResponse(BaseModel):
    lecture_id: str
    status: LectureStatus


class ConceptsResponse(BaseModel):
    lecture_id: str
    status: LectureStatus
    concepts: list[Concept]
    error: str | None = None  # set when status == "failed"
    title: str = ""
    page_count: int = 0
    overview: str = ""  # Markdown, empty until status == "ready"


class SessionRequest(BaseModel):
    lecture_id: str = Field(min_length=1, max_length=64)
    # The concepts the student dragged into the review box. Omitted or empty = the whole lecture.
    concept_ids: list[str] = Field(default_factory=list, max_length=100)


class SessionResponse(BaseModel):
    session_id: str
    questions: list[Question]


class SessionState(BaseModel):
    """GET /api/sessions/{id}: everything a page needs after a reload."""

    session_id: str
    lecture_id: str
    concept_ids: list[str]
    scope_summary: str
    preferences: Preferences
    chat: list[ChatMessage]
    current_question: Question | None
    mastery: list[Mastery]
    answered: int
    done: bool


class Bookmark(BaseModel):
    """A question the student starred during a quiz (the 'mistake book'); kept per lecture."""

    question_id: str
    session_id: str
    added_at: str = Field(default_factory=now_iso)


class BookmarkRequest(BaseModel):
    question_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=64)


class BookmarkItem(BaseModel):
    question: Question
    concept_name: str
    your_answer: str | None = None  # what the student answered in that session, if anything
    correct: bool | None = None
    added_at: str
    session_id: str


class BookmarksResponse(BaseModel):
    lecture_id: str
    items: list[BookmarkItem]


class LectureMastery(BaseModel):
    """Mastery across every session of a lecture: colours the concept boxes on the main page."""

    lecture_id: str
    mastery: list[Mastery]
    sessions: int


class PreferencesUpdate(BaseModel):
    question_type: QuestionType | None = None
    difficulty: Literal["easier", "same", "harder"] | None = None
    clear_question_type: bool = False  # back to "the agent decides"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    preferences: Preferences  # after this message; the quiz page shows what changed
    changed: list[str]  # e.g. ["question_type"], empty when the message was only a question


class LecturePage(BaseModel):
    page: int
    title: str
    page_type: str
    text: str  # the page's text layer, trimmed
    concept_ids: list[str]  # concepts taught on this page


class PagesResponse(BaseModel):
    lecture_id: str
    pages: list[LecturePage]


class AnswerRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    question_id: str = Field(min_length=1, max_length=64)
    answer: str = Field(min_length=1, max_length=4000)


class AnswerResponse(BaseModel):
    correct: bool
    concept_id: str
    feedback: str
    citation: Citation | None = None
    mastery: list[Mastery]
    next_action: NextAction
    next_questions: list[Question]


class TraceResponse(BaseModel):
    events: list[TraceEvent]


class Flashcard(BaseModel):
    front: str
    back: str
    concept_id: str
    page: int


class NotesResponse(BaseModel):
    summary_markdown: str
    weak_concepts: list[str]
    flashcards: list[Flashcard]
