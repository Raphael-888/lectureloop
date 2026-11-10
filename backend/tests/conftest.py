"""Shared fixtures for the API and agent tests. No network: the offline model stands in."""

import os
import tempfile

# Set before app.main is imported, so the module-level app never touches real data or a real key.
_TMP = tempfile.mkdtemp(prefix="lectureloop-test-")
os.environ["LLM_PROVIDER"] = "offline"
os.environ["AGENT_PLANNER"] = "llm"
os.environ["DB_PATH"] = os.path.join(_TMP, "default.sqlite3")
os.environ["UPLOAD_DIR"] = os.path.join(_TMP, "uploads")

import pymupdf  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

# Five content slides. The offline model turns them into a chain:
# comparison_model <- insertion_sort <- merge_sort <- quicksort <- lower_bound
SLIDES = [
    ("Sorting algorithms", "CSCI 0000, week 4. An overview of comparison sorting."),
    (
        "Comparison model",
        "Sorting algorithms compare pairs of elements to decide their order.\n"
        "Each comparison gives one bit of information about the input.",
    ),
    (
        "Insertion sort",
        "Insertion sort grows a sorted prefix one element at a time.\n"
        "It takes quadratic time in the worst case but is fast on nearly sorted input.",
    ),
    (
        "Merge sort",
        "Merge sort splits the array in half, sorts each half and merges them.\n"
        "It always runs in n log n time and needs linear extra space.",
    ),
    (
        "Quicksort",
        "Quicksort partitions the array around a pivot and recurses on both sides.\n"
        "Its expected running time is n log n with a random pivot.",
    ),
    (
        "Lower bound",
        "Any comparison sort needs about n log n comparisons in the worst case.\n"
        "The decision tree argument proves this bound for every such algorithm.",
    ),
]
CHAIN = ["comparison_model", "insertion_sort", "merge_sort", "quicksort", "lower_bound"]


def make_pdf(slides=SLIDES) -> bytes:
    doc = pymupdf.open()
    for title, body in slides:
        page = doc.new_page()
        page.insert_text((72, 90), title, fontsize=22)
        page.insert_text((72, 150), body, fontsize=12)
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    from app.main import create_app
    from app.store import Store

    app = create_app(Store(tmp_path / "test.sqlite3"))
    with TestClient(app) as c:
        yield c


@pytest.fixture
def store(client):
    return client.app.state.store


@pytest.fixture
def lecture_id(client):
    """An uploaded, fully processed lecture (background tasks finish inside TestClient)."""
    r = client.post("/api/lectures", files={"file": ("sorting.pdf", make_pdf(), "application/pdf")})
    assert r.status_code == 202, r.text
    return r.json()["lecture_id"]


def right_answer(store, session_id: str, question_id: str) -> str:
    item = store.get_session(session_id).issued[question_id]
    return item.answer if item.type == "multiple_choice" else item.reference


def wrong_answer(store, session_id: str, question_id: str) -> str:
    item = store.get_session(session_id).issued[question_id]
    if item.type == "multiple_choice":
        return next(letter for letter in "ABCD" if letter != item.answer)
    return "I am not sure."


def play(client, store, lecture_id: str, fail=frozenset(), max_questions: int = 60) -> dict:
    """Answer a whole session. Concepts in `fail` are always answered wrong."""
    r = client.post("/api/sessions", json={"lecture_id": lecture_id})
    assert r.status_code == 200, r.text
    session_id = r.json()["session_id"]
    question = r.json()["questions"][0]
    turns = []
    for _ in range(max_questions):
        give = wrong_answer if question["concept_id"] in fail else right_answer
        r = client.post(
            "/api/answers",
            json={
                "session_id": session_id,
                "question_id": question["id"],
                "answer": give(store, session_id, question["id"]),
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        turns.append({"question": question, **body})
        if body["next_action"] == "done":
            return {"session_id": session_id, "turns": turns}
        question = body["next_questions"][0]
    raise AssertionError("session did not finish")
