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

from app.agent.llm import LLMError, get_llm
from app.agent.loop import Agent, mastery_list
from app.config import get_settings
from app.errors import ApiError
from app.models import (
    AnswerRequest,
    AnswerResponse,
    ConceptsResponse,
    Lecture,
    NotesResponse,
    Session,
    SessionRequest,
    SessionResponse,
    TraceResponse,
    UploadResponse,
)
from app.output.notes import build_notes, flashcards_csv
from app.pipeline import process_lecture
from app.store import Store

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
            lecture_id=lecture.id, status=lecture.status, concepts=lecture.concepts, error=lecture.error
        )

    @app.post("/api/sessions", response_model=SessionResponse, response_model_exclude_none=True)
    def start_session(body: SessionRequest):
        lecture = lecture_or_404(body.lecture_id)
        if lecture.status != "ready":
            raise ApiError(409, "lecture_not_ready", f"Lecture {lecture.id} is {lecture.status}.")
        session = Session(id=f"s_{secrets.token_hex(12)}", lecture_id=lecture.id)
        questions = Agent(app.state.store, lecture, session, get_settings()).start()
        app.state.store.save_session(session)
        return SessionResponse(session_id=session.id, questions=questions)

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
