"""Selected-concept review: scope, tutor chat and preferences, driven through the Agent directly.

No PDF, no HTTP: the lecture is built by hand, so this file runs with only pydantic and sqlite
(and the offline model). The API routes for the same flow are covered in test_api_flow.py.
"""

from dataclasses import replace

import pytest

from app.agent.chat import chat
from app.agent.llm import Asker
from app.agent.loop import Agent
from app.agent.offline_llm import OfflineLLM
from app.agent.summarize import summarize
from app.config import get_settings
from app.learner.review import review_scope
from app.models import Lecture, Session, SlidePage
from app.output.notes import build_notes
from app.schemas import Concept
from app.store import Store

SETTINGS = replace(get_settings(), planner="rules", max_attempts=4, enable_short_answer=True)

# comparison_model <- insertion_sort <- merge_sort <- quicksort <- lower_bound
CHAIN = [
    ("comparison_model", "Comparison model", "Sorting algorithms compare pairs of elements to decide order.", 2, []),
    ("insertion_sort", "Insertion sort", "Insertion sort grows a sorted prefix one element at a time.", 3, ["comparison_model"]),
    ("merge_sort", "Merge sort", "Merge sort splits the array in half, sorts each half and merges them.", 4, ["insertion_sort"]),
    ("quicksort", "Quicksort", "Quicksort partitions the array around a pivot and recurses on both sides.", 5, ["merge_sort"]),
    ("lower_bound", "Lower bound", "Any comparison sort needs about n log n comparisons in the worst case.", 6, ["quicksort"]),
]


def make_lecture() -> Lecture:
    pages = [SlidePage(page=1, title="Sorting algorithms", page_type="title", text="Sorting algorithms. Week 4.")]
    concepts = []
    for cid, name, summary, page, pre in CHAIN:
        pages.append(SlidePage(page=page, title=name, page_type="content", text=f"{name}\n{summary}\nMore detail here."))
        concepts.append(Concept(id=cid, name=name, summary=summary, pages=[page], prerequisites=pre))
    return Lecture(id="l_test", filename="sorting.pdf", title="Sorting", status="ready", pages=pages, concepts=concepts)


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "test.sqlite3")


def start(store, lecture, targets):
    session = Session(id="s_test", lecture_id=lecture.id, targets=review_scope(targets, [c.model_dump() for c in lecture.concepts]))
    session.scope_summary = summarize(Asker(OfflineLLM(), store, session.id), lecture, [c for c in lecture.concepts if c.id in targets])
    agent = Agent(store, lecture, session, SETTINGS, llm=OfflineLLM())
    return session, agent, agent.start()[0]


def right(session, qid):
    item = session.issued[qid]
    return item.answer if item.type == "multiple_choice" else item.reference


def wrong(session, qid):
    item = session.issued[qid]
    return next(x for x in "ABCD" if x != item.answer) if item.type == "multiple_choice" else "no idea"


def play(store, lecture, targets, fail=frozenset(), limit=40):
    session, agent, q = start(store, lecture, targets)
    turns = []
    for _ in range(limit):
        answer = wrong(session, q.id) if q.concept_id in fail else right(session, q.id)
        r = agent.answer(q.id, answer)
        turns.append((q.concept_id, r))
        if r.next_action == "done":
            return session, turns
        q = r.next_questions[0]
    raise AssertionError("did not finish")


def test_scope_covers_only_the_selected_concepts(store):
    lecture = make_lecture()
    session, turns = play(store, lecture, ["merge_sort", "quicksort"])
    assert {cid for cid, _ in turns} == {"merge_sort", "quicksort"}
    assert turns[0][0] == "quicksort"  # most advanced selected concept first
    assert session.done
    assert [e.tool for e in session.trace][:4] == ["extract_concepts", "review_scope", "summarize", "generate_quiz"]
    assert "2 of 5 concepts" in session.trace[1].summary
    assert session.scope_summary.startswith("This review covers Merge sort, Quicksort")


def test_wrong_answer_may_test_a_prerequisite_outside_the_selection(store):
    """Fail quicksort: the gap is traced to merge_sort even though only quicksort was selected."""
    lecture = make_lecture()
    session, agent, q = start(store, lecture, ["quicksort"])
    r = agent.answer(q.id, wrong(session, q.id))
    assert r.next_action == "test_prerequisite"
    assert r.next_questions[0].concept_id == "merge_sort"
    assert "outside the selection" in [e for e in session.trace if e.tool == "trace_root_cause"][-1].summary
    # merge_sort is fine (the agent confirms it with a second question, then returns):
    # quicksort itself is the root cause -> explain it with a slide citation and re-test it
    for _ in range(5):
        q = r.next_questions[0]
        r = agent.answer(q.id, right(session, q.id))
        if q.concept_id == "merge_sort" and r.next_action == "next_question":
            continue
        break
    assert r.next_action == "explain"
    assert r.next_questions[0].concept_id == "quicksort"
    assert r.citation and r.citation.page == 5


def test_session_finishes_when_the_scope_is_mastered_even_if_a_prerequisite_was_tested(store):
    lecture = make_lecture()
    session, turns = play(store, lecture, ["quicksort"], fail={"quicksort"})
    assert session.done
    tested = {cid for cid, _ in turns}
    assert "quicksort" in tested
    assert tested <= {"quicksort", "merge_sort", "insertion_sort", "comparison_model"}
    notes = build_notes(lecture, session)
    assert "What you reviewed" in notes.summary_markdown
    assert "quicksort" in notes.weak_concepts
    assert "Lower bound" not in notes.summary_markdown  # never selected, never tested


def test_empty_selection_means_the_whole_lecture(store):
    lecture = make_lecture()
    session, turns = play(store, lecture, [])
    assert {cid for cid, _ in turns} == {c.id for c in lecture.concepts}
    assert not any(e.tool == "review_scope" for e in session.trace)


def test_unknown_concept_is_rejected():
    lecture = make_lecture()
    with pytest.raises(ValueError):
        review_scope(["merge_sort", "bogus"], [c.model_dump() for c in lecture.concepts])


def test_chat_answers_from_the_slides_without_changing_settings(store):
    lecture = make_lecture()
    session, agent, _ = start(store, lecture, ["merge_sort"])
    r = chat(Asker(OfflineLLM(), store, session.id), lecture, session, "How does merge sort split the array?")
    assert r.changed == []
    assert "p. 4" in r.reply
    assert session.preferences.question_type is None
    assert [m.role for m in session.chat] == ["student", "tutor"]
    assert session.trace[-1].tool == "chat"
    assert not session.p  # chatting is never graded


def test_chat_changes_question_type_and_difficulty(store):
    lecture = make_lecture()
    session, agent, q = start(store, lecture, ["merge_sort", "quicksort"])
    assert q.type == "multiple_choice"
    r = chat(Asker(OfflineLLM(), store, session.id), lecture, session, "Give me short answer questions, and make them harder")
    assert set(r.changed) == {"question_type", "difficulty"}
    assert session.preferences.question_type == "short_answer"
    assert session.preferences.difficulty == "harder"
    assert "short-answer" in r.reply and "harder" in r.reply
    # the next question handed out follows the new preference
    r2 = agent.answer(q.id, right(session, q.id))
    assert r2.next_questions[0].type == "short_answer"
    assert session.issued[r2.next_questions[0].id].difficulty == "harder"


def test_chat_back_to_multiple_choice(store):
    lecture = make_lecture()
    session, agent, q = start(store, lecture, ["merge_sort"])
    chat(Asker(OfflineLLM(), store, session.id), lecture, session, "short answer please")
    r = chat(Asker(OfflineLLM(), store, session.id), lecture, session, "actually multiple choice is fine")
    assert r.changed == ["question_type"]
    assert session.preferences.question_type == "multiple_choice"


# ---------- Nov 12: starred questions come first in later sessions ----------


def test_starred_question_is_asked_first_next_time(store):
    from app.models import Bookmark

    lecture = make_lecture()
    session, agent, q1 = start(store, lecture, ["merge_sort"])
    bank = store.list_questions(lecture.id, "merge_sort")
    assert len(bank) >= 2 and bank[0].id == q1.id  # a fresh session starts at the top of the bank

    lecture.bookmarks.append(Bookmark(question_id=bank[-1].id, session_id=session.id))
    _, _, q_starred = start(store, lecture, ["merge_sort"])
    assert q_starred.id == bank[-1].id
