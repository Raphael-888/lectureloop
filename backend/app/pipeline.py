"""Background job for one upload: PDF -> pages -> concept graph (C's code) -> question bank."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from app.agent.llm import LLM, Asker, LLMError, Metered, get_llm
from app.agent.quiz import prefill_bank
from app.concepts.extract import ExtractionError, extract_graph
from app.config import Settings
from app.models import Lecture, SlidePage
from app.retrieval.merge import merge
from app.retrieval.pdf_parser import Page, parse_pdf, render_page_images
from app.store import Store

log = logging.getLogger("lectureloop.pipeline")


def page_image_dir(settings: Settings, lecture_id: str) -> Path:
    """Where a lecture's rendered slide images live (GET /api/lectures/{id}/pages/{page}/image)."""
    return settings.upload_dir / "pages" / lecture_id


class LectureRejected(Exception):
    """The PDF cannot be used; the message is safe to show to the student."""


def _build(lecture: Lecture, pdf_path: Path, settings: Settings, llm: LLM, store: Store) -> None:
    started = time.perf_counter()
    try:
        pages = parse_pdf(pdf_path)
    except Exception as e:  # corrupted or password-protected file
        raise LectureRejected("This file could not be read as a PDF.") from e
    if len(pages) > settings.max_pages:
        raise LectureRejected(f"This PDF has {len(pages)} pages; the limit is {settings.max_pages}.")

    # No vision transcript in the upload flow yet: text layer only (see C's scripts/run_vision.py).
    records = merge(pages, {})
    lecture.pages = [
        SlidePage(page=r.page, title=r.title or "", page_type=r.page_type, text=r.text or r.rich_text)
        for r in records
    ]
    # The file name is what the student recognises; a title page often starts with a print timestamp.
    lecture.title = Path(lecture.filename).stem or next((r.title for r in records if r.title), "")
    content = [
        Page(page=r.page, slide_no=r.slide_no, title=r.title or "", text=r.rich_text, needs_vision=False)
        for r in records
        if r.page_type == "content" and r.rich_text
    ]
    if not content:
        raise LectureRejected("No readable text found. Scanned or image-only slides are not supported yet.")
    lecture.timings["parse_s"] = round(time.perf_counter() - started, 2)

    started = time.perf_counter()
    try:
        graph = extract_graph(content, Metered(llm, store, lecture.id, "extract_concepts"))
    except ExtractionError as e:
        raise LectureRejected("The agent could not build a valid concept graph from these slides.") from e
    lecture.concepts = graph.concepts
    lecture.timings["extract_s"] = round(time.perf_counter() - started, 2)


def process_lecture(
    store: Store, lecture_id: str, pdf_path: Path, settings: Settings, llm: LLM | None = None
) -> None:
    lecture = store.get_lecture(lecture_id)
    if lecture is None:
        return
    upload_started = time.perf_counter()
    try:
        llm = llm or get_llm()
        _build(lecture, pdf_path, settings, llm, store)
        lecture.status = "ready"
        try:
            # keep a picture of each slide for the review page; the PDF itself is still deleted below
            render_page_images(pdf_path, page_image_dir(settings, lecture.id), max_pages=settings.max_pages)
        except Exception:
            log.warning("lecture %s: could not render page images; the text view is used instead", lecture_id)
    except LectureRejected as e:
        lecture.status, lecture.error = "failed", str(e)
    except LLMError as e:
        log.warning("lecture %s: %s", lecture_id, e)
        lecture.status, lecture.error = "failed", "The language model is not available. Try again later."
    except Exception:
        log.exception("lecture %s failed", lecture_id)
        lecture.status, lecture.error = "failed", "Processing failed unexpectedly."
    finally:
        pdf_path.unlink(missing_ok=True)  # keep the extracted text and page images, not the uploaded file
    lecture.timings["ready_s"] = round(time.perf_counter() - upload_started, 2)
    store.save_lecture(lecture)
    if lecture.status != "ready":
        return

    # The lecture is already usable; questions that are not ready yet are generated on demand.
    started = time.perf_counter()
    count = prefill_bank(store, lecture, Asker(llm, store, lecture.id))
    lecture.timings["question_bank_s"] = round(time.perf_counter() - started, 2)
    store.save_lecture(lecture)
    log.info("lecture %s ready: %d concepts, %d questions", lecture_id, len(lecture.concepts), count)
