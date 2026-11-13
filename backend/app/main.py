"""FastAPI app. Routes follow docs/api-contract.md; update that file when changing them.

Run from backend/:  uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
import secrets
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException

from app.agent.chat import chat as tutor_chat
from app.agent.llm import Asker, LLMError, get_llm
from app.agent.loop import Agent, _NoLLM, mastery_list
from app.agent.summarize import summarize
from app.config import get_settings
from app.errors import ApiError
from app.learner.review import review_scope
from app.learner.bkt import label_for, params_for
from app.models import (
    AnswerRequest,
    AnswerResponse,
    Bookmark,
    BookmarkItem,
    BookmarkRequest,
    BookmarksResponse,
    ChatRequest,
    ChatResponse,
    ConceptsResponse,
    Lecture,
    LectureMastery,
    LecturePage,
    Mastery,
    NotesResponse,
    PagesResponse,
    PreferencesUpdate,
    Session,
    SessionRequest,
    SessionResponse,
    SessionState,
    TraceResponse,
    UploadResponse,
)
from app.output.notes import build_notes, flashcards_csv
from app.pipeline import process_lecture
from app.store import Store

PAGE_TEXT_CHARS = 1200  # per page in GET /lectures/{id}/pages

log = logging.getLogger("lectureloop.api")


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def create_app(store: Store | None = None) -> FastAPI:
    app = FastAPI(title="LectureLoop API", version="0.1.0")
    app.state.store = store or Store(get_settings().db_path)

    # ---------- errors: always the contract's envelope, never a stack trace ----------

    @app.exception_handler(ApiError)
    async def api_error(_: Request, e: ApiError):
        return _error(e.status, e.code, e.message)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, e: RequestValidationError):
        first = e.errors()[0] if e.errors() else {}
        where = ".".join(str(part) for part in first.get("loc", []) if part != "body")
        return _error(422, "invalid_request", f"{where}: {first.get('msg', 'invalid value')}".strip(": "))

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, e: HTTPException):
        return _error(e.status_code, f"http_{e.status_code}", str(e.detail))

    @app.exception_handler(Exception)
    async def unexpected(_: Request, e: Exception):
        log.exception("unhandled error", exc_info=e)
        return _error(500, "internal_error", "Something went wrong on the server.")

    # ---------- lookups ----------

    def lecture_or_404(lecture_id: str) -> Lecture:
        lecture = app.state.store.get_lecture(lecture_id)
        if lecture is None:
            raise ApiError(404, "lecture_not_found", f"No lecture with id {lecture_id}")
        return lecture

    def session_or_404(session_id: str) -> Session:
        session = app.state.store.get_session(session_id)
        if session is None:
            raise ApiError(404, "session_not_found", f"No session with id {session_id}")
        return session

    # ---------- routes ----------

    @app.get("/api/health")
    def health():
        s = get_settings()
        try:
            get_llm()
            llm = s.llm_provider
        except LLMError:
            llm = "not_configured"
        return {"status": "ok", "llm": llm, "planner": s.planner}

    @app.post("/api/lectures", status_code=202, response_model=UploadResponse)
    def upload_lecture(background: BackgroundTasks, file: UploadFile = File(...)):  # noqa: B008
        s = get_settings()
        limit = s.max_upload_mb * 1024 * 1024
        name = Path(file.filename or "lecture.pdf").name[:120]  # display only; never used as a path
        data = file.file.read(limit + 1)
        if len(data) > limit:
            raise ApiError(413, "file_too_large", f"The file is larger than {s.max_upload_mb} MB.")
        if not name.lower().endswith(".pdf") or b"%PDF-" not in data[:1024]:
            raise ApiError(415, "unsupported_file_type", "Please upload a PDF file.")
        try:
            get_llm()
        except LLMError as e:
            raise ApiError(503, "llm_not_configured", "The server has no language model configured.") from e

        lecture = Lecture(id=f"l_{secrets.token_hex(8)}", filename=name)
        s.upload_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = s.upload_dir / f"{lecture.id}.pdf"
        pdf_path.write_bytes(data)
        app.state.store.save_lecture(lecture)
        background.add_task(process_lecture, app.state.store, lecture.id, pdf_path, s)
        return UploadResponse(lecture_id=lecture.id, status=lecture.status)

    @app.get("/api/lectures/{lecture_id}/concepts", response_model=ConceptsResponse)
    def get_concepts(lecture_id: str):
        lecture = lecture_or_404(lecture_id)
        return ConceptsResponse(
            lecture_id=lecture.id,
            status=lecture.status,
            concepts=lecture.concepts,
            error=lecture.error,
            title=lecture.title,
            page_count=len(lecture.pages),
            overview=lecture.overview if lecture.status == "ready" else "",
        )

    @app.get("/api/lectures/{lecture_id}/pages", response_model=PagesResponse)
    def get_pages(lecture_id: str, concept_ids: str = Query("", max_length=4000)):
        """The slides' text, for the 'original PDF' view. concept_ids (comma-separated) filters
        to the pages that teach those concepts; empty = every page."""
        lecture = lecture_or_404(lecture_id)
        if lecture.status != "ready":
            raise ApiError(409, "lecture_not_ready", f"Lecture {lecture.id} is {lecture.status}.")
        wanted = {cid.strip() for cid in concept_ids.split(",") if cid.strip()}
        taught: dict[int, list[str]] = {}
        for c in lecture.concepts:
            for page in c.pages:
                taught.setdefault(page, []).append(c.id)
        pages = [
            LecturePage(
                page=p.page,
                title=p.title,
                page_type=p.page_type,
                text=p.text[:PAGE_TEXT_CHARS],
                concept_ids=taught.get(p.page, []),
            )
            for p in lecture.pages
            if not wanted or wanted & set(taught.get(p.page, []))
        ]
        return PagesResponse(lecture_id=lecture.id, pages=pages)

    @app.get("/api/lectures/{lecture_id}/mastery", response_model=LectureMastery)
    def get_lecture_mastery(lecture_id: str):
        """Mastery per concept across every session of the lecture: the most recent session that
        tested a concept wins. Colours the concept boxes on the main page."""
        lecture = lecture_or_404(lecture_id)
        sessions = app.state.store.list_sessions(lecture.id)
        latest: dict[str, float] = {}
        for session in sessions:  # oldest first, so later sessions overwrite
            latest.update(session.p)
        prior = params_for()["prior"]
        mastery = [
            Mastery(
                concept_id=c.id,
                p_mastery=round(latest.get(c.id, prior), 3),
                label=label_for(latest.get(c.id, prior), tested=c.id in latest),
            )
            for c in lecture.concepts
        ]
        return LectureMastery(lecture_id=lecture.id, mastery=mastery, sessions=len(sessions))

    def _bookmarks(lecture: Lecture) -> BookmarksResponse:
        store: Store = app.state.store
        names = {c.id: c.name for c in lecture.concepts}
        items = []
        for b in lecture.bookmarks:
            item = store.get_question(b.question_id)
            if item is None:
                continue
            session = store.get_session(b.session_id)
            answered = session.answers.get(b.question_id) if session else None
            logged = [a for a in store.list_answers(b.session_id) if a["question_id"] == b.question_id]
            correct = bool(logged[-1]["correct"]) if logged else None
            items.append(
                BookmarkItem(
                    question=item.public(),
                    concept_name=names.get(item.concept_id, item.concept_id),
                    your_answer=answered,
                    correct=correct,
                    added_at=b.added_at,
                    session_id=b.session_id,
                )
            )
        items.sort(key=lambda i: i.added_at, reverse=True)
        return BookmarksResponse(lecture_id=lecture.id, items=items)

    @app.get("/api/lectures/{lecture_id}/bookmarks", response_model=BookmarksResponse, response_model_exclude_none=True)
    def get_bookmarks(lecture_id: str):
        return _bookmarks(lecture_or_404(lecture_id))

    @app.post("/api/lectures/{lecture_id}/bookmarks", response_model=BookmarksResponse, response_model_exclude_none=True)
    def toggle_bookmark(lecture_id: str, body: BookmarkRequest):
        """Star or un-star a question. Starred questions are asked first in later sessions."""
        store: Store = app.state.store
        with store.lock(lecture_id):
            lecture = lecture_or_404(lecture_id)
            if store.get_question(body.question_id) is None:
                raise ApiError(404, "question_not_found", f"No question {body.question_id}.")
            before = len(lecture.bookmarks)
            lecture.bookmarks = [b for b in lecture.bookmarks if b.question_id != body.question_id]
            if len(lecture.bookmarks) == before:
                lecture.bookmarks.append(Bookmark(question_id=body.question_id, session_id=body.session_id))
            store.save_lecture(lecture)
            return _bookmarks(lecture)

    def _asker(session: Session) -> Asker:
        try:
            llm = get_llm()
        except LLMError:
            llm = _NoLLM()
        return Asker(llm, app.state.store, session.id)

    @app.post("/api/sessions", response_model=SessionResponse, response_model_exclude_none=True)
    def start_session(body: SessionRequest):
        lecture = lecture_or_404(body.lecture_id)
        if lecture.status != "ready":
            raise ApiError(409, "lecture_not_ready", f"Lecture {lecture.id} is {lecture.status}.")
        try:
            targets = review_scope(body.concept_ids, [c.model_dump() for c in lecture.concepts])  # D: validated
        except ValueError as e:
            raise ApiError(422, "unknown_concept", str(e)) from e
        session = Session(id=f"s_{secrets.token_hex(12)}", lecture_id=lecture.id, targets=targets)
        scope = [c for c in lecture.concepts if c.id in targets] if targets else lecture.concepts
        session.scope_summary = summarize(_asker(session), lecture, scope)
        questions = Agent(app.state.store, lecture, session, get_settings()).start()
        app.state.store.save_session(session)
        return SessionResponse(session_id=session.id, questions=questions)

    @app.get("/api/sessions/{session_id}", response_model=SessionState, response_model_exclude_none=True)
    def get_session(session_id: str):
        session = session_or_404(session_id)
        lecture = lecture_or_404(session.lecture_id)
        current = session.issued.get(session.current_question or "")
        return SessionState(
            session_id=session.id,
            lecture_id=lecture.id,
            concept_ids=session.targets or [c.id for c in lecture.concepts],
            scope_summary=session.scope_summary,
            preferences=session.preferences,
            chat=session.chat,
            current_question=current.public() if current else None,
            mastery=mastery_list(lecture, session),
            answered=len(session.answers),
            done=session.done,
        )

    @app.patch("/api/sessions/{session_id}/preferences", response_model=SessionState, response_model_exclude_none=True)
    def patch_preferences(session_id: str, body: PreferencesUpdate):
        """The question-type / difficulty picker on the quiz page (the chat can do the same)."""
        store: Store = app.state.store
        with store.lock(session_id):
            session = session_or_404(session_id)
            lecture = lecture_or_404(session.lecture_id)
            changed = []
            if body.clear_question_type and session.preferences.question_type is not None:
                session.preferences.question_type = None
                changed.append("question_type=agent")
            elif body.question_type and body.question_type != session.preferences.question_type:
                session.preferences.question_type = body.question_type
                changed.append(f"question_type={body.question_type}")
            if body.difficulty and body.difficulty != session.preferences.difficulty:
                session.preferences.difficulty = body.difficulty
                changed.append(f"difficulty={body.difficulty}")
            if changed:
                session.add_trace("preferences", "The student changed the quiz settings", ", ".join(changed))
                store.save_session(session)
        return get_session(session_id)

    @app.post("/api/sessions/{session_id}/finish", response_model=SessionState, response_model_exclude_none=True)
    def finish_session(session_id: str):
        """The 'End' button: stop quizzing now. Mastery so far is kept; notes are available."""
        store: Store = app.state.store
        with store.lock(session_id):
            session = session_or_404(session_id)
            if not session.done:
                session.done = True
                session.current_question = None
                session.stack = []
                session.add_trace("finish", "The student ended the quiz early", f"Stopped after {len(session.answers)} answers")
                store.save_session(session)
        return get_session(session_id)

    @app.post("/api/sessions/{session_id}/chat", response_model=ChatResponse)
    def post_chat(session_id: str, body: ChatRequest):
        store: Store = app.state.store
        with store.lock(session_id):
            session = session_or_404(session_id)
            lecture = lecture_or_404(session.lecture_id)
            response = tutor_chat(_asker(session), lecture, session, body.message)
            store.save_session(session)
        return response

    @app.post("/api/answers", response_model=AnswerResponse, response_model_exclude_none=True)
    def submit_answer(body: AnswerRequest):
        store: Store = app.state.store
        with store.lock(body.session_id):  # one answer at a time per session
            session = session_or_404(body.session_id)
            lecture = lecture_or_404(session.lecture_id)
            response = Agent(store, lecture, session, get_settings()).answer(body.question_id, body.answer)
            store.save_session(session)
        return response

    @app.get("/api/sessions/{session_id}/trace", response_model=TraceResponse)
    def get_trace(session_id: str, after_step: int = Query(0, ge=0)):
        session = session_or_404(session_id)
        return TraceResponse(events=[e for e in session.trace if e.step > after_step])

    @app.get("/api/sessions/{session_id}/notes", response_model=NotesResponse)
    def get_notes(session_id: str):
        session = session_or_404(session_id)
        return build_notes(lecture_or_404(session.lecture_id), session)

    @app.get("/api/sessions/{session_id}/flashcards.csv")
    def get_flashcards_csv(session_id: str):
        session = session_or_404(session_id)
        body = flashcards_csv(build_notes(lecture_or_404(session.lecture_id), session))
        headers = {"Content-Disposition": 'attachment; filename="lectureloop-flashcards.csv"'}
        return Response(content=body, media_type="text/csv; charset=utf-8", headers=headers)

    @app.get("/api/sessions/{session_id}/log")
    def get_log(session_id: str):
        """Evaluation data for D: answers, diagnoses, timings and model usage. Not used by the UI."""
        store: Store = app.state.store
        session = session_or_404(session_id)
        lecture = lecture_or_404(session.lecture_id)
        return {
            "session_id": session.id,
            "lecture_id": lecture.id,
            "done": session.done,
            "answers": store.list_answers(session.id),
            "root_causes": [r.model_dump() for r in session.root_causes],
            "mastery": [m.model_dump() for m in mastery_list(lecture, session)],
            "lecture_timings_s": lecture.timings,
            "llm_usage": {"lecture": store.llm_usage(lecture.id), "session": store.llm_usage(session.id)},
        }

    return app


app = create_app()
