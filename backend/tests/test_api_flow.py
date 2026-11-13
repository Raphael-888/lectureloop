"""End-to-end API tests: upload -> concepts -> session -> answers -> trace -> notes."""

import csv
import io

from tests.conftest import CHAIN, make_pdf, play, right_answer, wrong_answer


def test_upload_builds_concept_graph(client, lecture_id):
    body = client.get(f"/api/lectures/{lecture_id}/concepts").json()
    assert body["status"] == "ready"
    assert [c["id"] for c in body["concepts"]] == CHAIN
    assert body["concepts"][1]["prerequisites"] == ["comparison_model"]
    assert body["concepts"][0]["pages"] == [2]


def test_uploaded_pdf_is_deleted_after_parsing(client, lecture_id, tmp_path):
    assert list((tmp_path / "uploads").glob("*.pdf")) == []


def test_all_correct_covers_and_masters_every_concept(client, store, lecture_id):
    result = play(client, store, lecture_id)
    turns = result["turns"]
    assert {t["concept_id"] for t in turns} == set(CHAIN)  # coverage: every concept was tested
    assert all(t["correct"] for t in turns)
    assert {m["label"] for m in turns[-1]["mastery"]} == {"mastered"}
    assert turns[-1]["next_questions"] == []
    # most advanced concept first, so a gap can be traced backwards
    assert turns[0]["concept_id"] == "lower_bound"


def test_questions_never_leak_the_answer_key(client, store, lecture_id):
    result = play(client, store, lecture_id)
    for turn in result["turns"]:
        assert set(turn["question"]) <= {"id", "concept_id", "type", "prompt", "options"}
        if turn["question"]["type"] == "short_answer":
            assert "options" not in turn["question"]


def test_wrong_answer_is_traced_back_to_the_root_cause(client, store, lecture_id):
    """Fail the two most basic concepts: the agent must walk back to them one level at a time."""
    session = client.post("/api/sessions", json={"lecture_id": lecture_id}).json()
    sid, question = session["session_id"], session["questions"][0]
    assert question["concept_id"] == "lower_bound"

    visited = []
    for expected_next in ["quicksort", "merge_sort", "insertion_sort", "comparison_model"]:
        body = client.post(
            "/api/answers",
            json={
                "session_id": sid,
                "question_id": question["id"],
                "answer": wrong_answer(store, sid, question["id"]),
            },
        ).json()
        assert body["correct"] is False
        assert body["next_action"] == "test_prerequisite"
        question = body["next_questions"][0]
        assert question["concept_id"] == expected_next
        visited.append(expected_next)

    # comparison_model has no prerequisites: it is the root cause, so the agent explains it
    body = client.post(
        "/api/answers",
        json={
            "session_id": sid,
            "question_id": question["id"],
            "answer": wrong_answer(store, sid, question["id"]),
        },
    ).json()
    assert body["next_action"] == "explain"
    assert body["citation"]["page"] == 2
    slide = next(p for p in store.get_lecture(lecture_id).pages if p.page == 2)
    assert body["citation"]["quote"] in " ".join(slide.text.split())  # quoted from the slide, not invented
    assert body["next_questions"][0]["concept_id"] == "comparison_model"

    log = client.get(f"/api/sessions/{sid}/log").json()
    assert {"symptom": "lower_bound", "root": "comparison_model"}.items() <= log["root_causes"][0].items()

    tools = [e["tool"] for e in client.get(f"/api/sessions/{sid}/trace").json()["events"]]
    assert tools.count("trace_root_cause") == 5
    assert "search_slides" in tools and "explain" in tools


def test_failing_one_concept_is_diagnosed_and_session_still_ends(client, store, lecture_id):
    """D's evaluation: answer one chosen concept wrong on purpose and check the diagnosis."""
    result = play(client, store, lecture_id, fail={"merge_sort"})
    sid = result["session_id"]
    log = client.get(f"/api/sessions/{sid}/log").json()
    assert [r["root"] for r in log["root_causes"]] == ["merge_sort"]
    assert log["done"] is True

    notes = client.get(f"/api/sessions/{sid}/notes").json()
    assert notes["weak_concepts"] == ["merge_sort"]
    assert notes["flashcards"][0]["concept_id"] == "merge_sort"
    assert "Review these first" in notes["summary_markdown"]

    by_concept = {m["concept_id"]: m["label"] for m in log["mastery"]}
    assert by_concept["merge_sort"] == "not_mastered"
    assert by_concept["insertion_sort"] == "mastered"  # its prerequisite was checked and cleared
    merge_attempts = [a for a in log["answers"] if a["concept_id"] == "merge_sort"]
    assert len(merge_attempts) == 4  # MAX_ATTEMPTS_PER_CONCEPT, then the agent moves on


def test_trace_is_ordered_and_supports_after_step(client, store, lecture_id):
    sid = play(client, store, lecture_id)["session_id"]
    events = client.get(f"/api/sessions/{sid}/trace").json()["events"]
    assert [e["step"] for e in events] == list(range(1, len(events) + 1))
    assert events[0]["tool"] == "extract_concepts" and events[-1]["tool"] == "export_flashcards"
    assert all(e["reason"] and e["summary"] and e["time"].endswith("Z") for e in events)
    later = client.get(f"/api/sessions/{sid}/trace", params={"after_step": 5}).json()["events"]
    assert [e["step"] for e in later] == list(range(6, len(events) + 1))


def test_flashcards_csv_is_importable(client, store, lecture_id):
    sid = play(client, store, lecture_id, fail={"quicksort"})["session_id"]
    r = client.get(f"/api/sessions/{sid}/flashcards.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(r.text)))
    assert len(rows) == len(CHAIN) + 1  # one card per concept, plus the missed question
    assert all(len(row) == 2 and "(slide p." in row[1] for row in rows)


def test_resubmitting_an_answer_does_not_update_mastery_twice(client, store, lecture_id):
    session = client.post("/api/sessions", json={"lecture_id": lecture_id}).json()
    sid, q = session["session_id"], session["questions"][0]
    payload = {"session_id": sid, "question_id": q["id"], "answer": right_answer(store, sid, q["id"])}
    first = client.post("/api/answers", json=payload).json()
    second = client.post("/api/answers", json=payload).json()
    assert first == second
    assert len(client.get(f"/api/sessions/{sid}/log").json()["answers"]) == 1


def test_errors_use_the_contract_envelope(client, store, lecture_id):
    def code(response):
        return response.status_code, response.json()["error"]["code"]

    assert code(client.get("/api/lectures/l_missing/concepts")) == (404, "lecture_not_found")
    assert code(client.post("/api/sessions", json={"lecture_id": "l_missing"})) == (404, "lecture_not_found")
    assert code(client.get("/api/sessions/s_missing/trace")) == (404, "session_not_found")
    assert code(client.post("/api/sessions", json={})) == (422, "invalid_request")
    assert code(client.get("/api/nope")) == (404, "http_404")

    session = client.post("/api/sessions", json={"lecture_id": lecture_id}).json()
    sid, q = session["session_id"], session["questions"][0]
    bad = {"session_id": sid, "question_id": "q_missing", "answer": "A"}
    assert code(client.post("/api/answers", json=bad)) == (404, "question_not_found")
    assert code(client.post("/api/answers", json={**bad, "question_id": q["id"], "answer": ""})) == (
        422,
        "invalid_request",
    )


def test_upload_validation(client, monkeypatch):
    def code(response):
        return response.status_code, response.json()["error"]["code"]

    pdf = make_pdf()
    assert code(client.post("/api/lectures", files={"file": ("notes.txt", b"hello", "text/plain")})) == (
        415,
        "unsupported_file_type",
    )
    # right extension, wrong content
    assert code(client.post("/api/lectures", files={"file": ("fake.pdf", b"<html>", "application/pdf")})) == (
        415,
        "unsupported_file_type",
    )
    monkeypatch.setenv("MAX_UPLOAD_MB", "0")
    assert code(client.post("/api/lectures", files={"file": ("big.pdf", pdf, "application/pdf")})) == (
        413,
        "file_too_large",
    )
    monkeypatch.delenv("MAX_UPLOAD_MB")
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert code(client.post("/api/lectures", files={"file": ("ok.pdf", pdf, "application/pdf")})) == (
        503,
        "llm_not_configured",
    )


def test_unreadable_pdf_fails_with_a_message(client):
    r = client.post(
        "/api/lectures", files={"file": ("broken.pdf", b"%PDF-1.7\nnot really a pdf", "application/pdf")}
    )
    assert r.status_code == 202
    body = client.get(f"/api/lectures/{r.json()['lecture_id']}/concepts").json()
    assert body["status"] == "failed" and body["error"] and body["concepts"] == []
    assert (
        client.post("/api/sessions", json={"lecture_id": body["lecture_id"]}).json()["error"]["code"]
        == "lecture_not_ready"
    )


# ---------- selected-concept review (Nov 10 product decision) ----------


def test_concepts_response_carries_title_pages_and_overview(client, lecture_id):
    body = client.get(f"/api/lectures/{lecture_id}/concepts").json()
    assert body["title"] == "sorting"
    assert body["page_count"] == 6
    assert "Comparison model" in body["overview"]


def test_pages_filtered_by_selected_concepts(client, lecture_id):
    everything = client.get(f"/api/lectures/{lecture_id}/pages").json()["pages"]
    assert [p["page"] for p in everything] == [1, 2, 3, 4, 5, 6]
    assert everything[1]["concept_ids"] == ["comparison_model"]
    some = client.get(f"/api/lectures/{lecture_id}/pages?concept_ids=merge_sort,quicksort").json()["pages"]
    assert [p["page"] for p in some] == [4, 5]
    assert "Merge sort" in some[0]["text"]


def test_scoped_session_quizzes_only_the_selection(client, store, lecture_id):
    r = client.post("/api/sessions", json={"lecture_id": lecture_id, "concept_ids": ["merge_sort", "quicksort"]})
    assert r.status_code == 200, r.text
    sid, question = r.json()["session_id"], r.json()["questions"][0]
    assert question["concept_id"] == "quicksort"

    state = client.get(f"/api/sessions/{sid}").json()
    assert state["concept_ids"] == ["merge_sort", "quicksort"]
    assert state["current_question"]["id"] == question["id"]
    assert "Merge sort" in state["scope_summary"]
    assert state["answered"] == 0 and state["done"] is False

    seen = set()
    for _ in range(20):
        body = client.post(
            "/api/answers",
            json={"session_id": sid, "question_id": question["id"], "answer": right_answer(store, sid, question["id"])},
        ).json()
        seen.add(body["concept_id"])
        if body["next_action"] == "done":
            break
        question = body["next_questions"][0]
    assert seen == {"merge_sort", "quicksort"}
    assert client.get(f"/api/sessions/{sid}").json()["done"] is True
    tools = [e["tool"] for e in client.get(f"/api/sessions/{sid}/trace").json()["events"]]
    assert tools[:4] == ["extract_concepts", "review_scope", "summarize", "generate_quiz"]


def test_unknown_concept_id_is_rejected(client, lecture_id):
    r = client.post("/api/sessions", json={"lecture_id": lecture_id, "concept_ids": ["nope"]})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "unknown_concept"


def test_chat_answers_and_changes_the_quiz(client, store, lecture_id):
    r = client.post("/api/sessions", json={"lecture_id": lecture_id, "concept_ids": ["merge_sort"]})
    sid, question = r.json()["session_id"], r.json()["questions"][0]

    r = client.post(f"/api/sessions/{sid}/chat", json={"message": "How does merge sort split the array?"})
    assert r.status_code == 200, r.text
    assert r.json()["changed"] == []
    assert "p. 4" in r.json()["reply"]

    r = client.post(f"/api/sessions/{sid}/chat", json={"message": "short answer questions please, harder"})
    assert set(r.json()["changed"]) == {"question_type", "difficulty"}
    assert r.json()["preferences"] == {"question_type": "short_answer", "difficulty": "harder"}

    state = client.get(f"/api/sessions/{sid}").json()
    assert [m["role"] for m in state["chat"]] == ["student", "tutor", "student", "tutor"]
    assert state["mastery"]  # chatting graded nothing
    assert all(m["label"] == "untested" for m in state["mastery"])

    body = client.post(
        "/api/answers",
        json={"session_id": sid, "question_id": question["id"], "answer": right_answer(store, sid, question["id"])},
    ).json()
    if body["next_questions"]:
        assert body["next_questions"][0]["type"] == "short_answer"


# ---------- Nov 12 meeting: main page colours, bookmarks, quiz settings, end button ----------


def test_lecture_mastery_aggregates_sessions(client, store, lecture_id):
    before = client.get(f"/api/lectures/{lecture_id}/mastery").json()
    assert before["sessions"] == 0
    assert all(m["label"] == "untested" for m in before["mastery"])

    r = client.post("/api/sessions", json={"lecture_id": lecture_id, "concept_ids": ["merge_sort"]})
    sid, q = r.json()["session_id"], r.json()["questions"][0]
    client.post("/api/answers", json={"session_id": sid, "question_id": q["id"], "answer": right_answer(store, sid, q["id"])})

    after = client.get(f"/api/lectures/{lecture_id}/mastery").json()
    assert after["sessions"] == 1
    merge = next(m for m in after["mastery"] if m["concept_id"] == "merge_sort")
    assert merge["label"] != "untested" and merge["p_mastery"] > 0.3


def test_bookmarks_toggle_and_list(client, store, lecture_id):
    r = client.post("/api/sessions", json={"lecture_id": lecture_id, "concept_ids": ["quicksort"]})
    sid, q = r.json()["session_id"], r.json()["questions"][0]
    assert client.get(f"/api/lectures/{lecture_id}/bookmarks").json()["items"] == []

    client.post("/api/answers", json={"session_id": sid, "question_id": q["id"], "answer": "Z"})
    r = client.post(f"/api/lectures/{lecture_id}/bookmarks", json={"question_id": q["id"], "session_id": sid})
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["question"]["id"] == q["id"]
    assert items[0]["concept_name"] == "Quicksort"
    assert items[0]["your_answer"] == "Z" and items[0]["correct"] is False
    assert "answer" not in items[0]["question"]  # never leak the key

    # toggling again removes it
    r = client.post(f"/api/lectures/{lecture_id}/bookmarks", json={"question_id": q["id"], "session_id": sid})
    assert r.json()["items"] == []

    r = client.post(f"/api/lectures/{lecture_id}/bookmarks", json={"question_id": "nope", "session_id": sid})
    assert r.status_code == 404


def test_preferences_endpoint_and_finish(client, store, lecture_id):
    r = client.post("/api/sessions", json={"lecture_id": lecture_id, "concept_ids": ["merge_sort", "quicksort"]})
    sid, q = r.json()["session_id"], r.json()["questions"][0]

    r = client.patch(f"/api/sessions/{sid}/preferences", json={"question_type": "short_answer", "difficulty": "harder"})
    assert r.status_code == 200, r.text
    assert r.json()["preferences"] == {"question_type": "short_answer", "difficulty": "harder"}
    r = client.patch(f"/api/sessions/{sid}/preferences", json={"clear_question_type": True})
    assert r.json()["preferences"]["question_type"] is None

    r = client.post(f"/api/sessions/{sid}/finish")
    assert r.status_code == 200
    assert r.json()["done"] is True and r.json()["current_question"] is None
    tools = [e["tool"] for e in client.get(f"/api/sessions/{sid}/trace").json()["events"]]
    assert tools[-1] == "finish" and "preferences" in tools
    # answering after the end is refused
    r = client.post("/api/answers", json={"session_id": sid, "question_id": q["id"], "answer": "A"})
    assert r.status_code in (409, 422)
    # notes still work
    assert client.get(f"/api/sessions/{sid}/notes").status_code == 200
