import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.concepts.extract import ExtractionError, extract_graph
from app.concepts.graph_check import check_graph, reduce_edges, to_mermaid
from app.llm import FileLLM
from app.retrieval.merge import merge
from app.retrieval.pdf_parser import Page, clean_page_text, parse_pdf
from app.schemas import Concept, ConceptGraph
from eval.compare_graph import compare

FIX = Path(__file__).parent / "fixtures"
LECTURES = FIX / "lectures"
M04 = LECTURES / "cs3151_m04.pdf"  # course material: kept out of git
M04_VISION = LECTURES / "cs3151_m04.vision.json"


def C(id, pages=(1,), pre=()):
    return Concept(id=id, name=id, summary="s", pages=list(pages), prerequisites=list(pre))


# ---------- schema ----------


def test_concept_rejects_bad_id_and_empty_pages():
    with pytest.raises(ValidationError) as exc:
        Concept(id="Bad ID!", name="Bad", summary="s", pages=[])
    bad_fields = {e["loc"][0] for e in exc.value.errors()}
    assert bad_fields == {"id", "pages"}


def test_concept_rejects_empty_summary():
    with pytest.raises(ValidationError):
        Concept(id="ok", name="Ok", summary="", pages=[1])


# ---------- pdf parser ----------


def test_clean_page_text_removes_print_noise():
    raw = (
        "2026-09-20, 12:21 PMM04: Title\n"
        "Page 6 of 36https://web.cs.dal.ca/x.html\n"
        "Expected vs empirical risk\n0.2\n0 2 4 6\nEmpirical risk (cost function)\n6\n"
    )
    text, slide_no = clean_page_text(raw)
    assert slide_no == 6
    assert text == "Expected vs empirical risk\nEmpirical risk (cost function)"


@pytest.mark.skipif(not M04.exists(), reason="lecture PDF not present")
def test_parse_real_lecture():
    pages = parse_pdf(str(M04))
    assert len(pages) == 36
    assert pages[5].title == "Expected vs empirical risk"
    assert "Empirical risk" in pages[5].text
    assert not any("Page " in p.text and "https://" in p.text for p in pages)
    assert pages[17].needs_vision  # page 18 is blank
    assert pages[18].slide_no == 18  # PDF page 19 shows slide number 18


# ---------- graph checks ----------


def test_good_graph_has_no_errors():
    g = ConceptGraph(concepts=[C("a"), C("b", pre=["a"])])
    assert check_graph(g, {1}) == []


@pytest.mark.parametrize(
    "concepts, expected",
    [
        ([C("a", pre=["b"]), C("b", pre=["a"])], "cycle"),
        ([C("a", pages=[99])], "pages [99]"),
        ([C("a", pre=["ghost"])], "'ghost' does not exist"),
        ([C("a", pre=["a"])], "own prerequisite"),
        ([C("a"), C("a")], "duplicate ids"),
    ],
)
def test_bad_graphs_are_caught(concepts, expected):
    errors = check_graph(ConceptGraph(concepts=concepts), {1})
    assert any(expected in e for e in errors), errors


def test_reduce_edges_drops_indirect_edge():
    g = ConceptGraph(concepts=[C("a"), C("b", pre=["a"]), C("c", pre=["a", "b"])])
    assert reduce_edges(g).concepts[2].prerequisites == ["b"]


def test_mermaid_output():
    g = ConceptGraph(concepts=[C("a"), C("b", pre=["a"])])
    assert "a --> b" in to_mermaid(g)


# ---------- extraction with a fake LLM ----------


class ScriptedLLM:
    """Returns the given answers in order and records the prompts it saw."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.prompts = []

    def complete_json(self, system, user):
        self.prompts.append(user)
        return self.answers.pop(0)


PAGES = [
    Page(1, 1, "Intro", "intro text", False),
    Page(2, 2, "Topic", "topic text", False),
]


def test_extract_retries_with_error_feedback():
    bad = json.dumps(
        {"concepts": [{"id": "x", "name": "X", "summary": "s", "pages": [7], "prerequisites": []}]}
    )
    good = json.dumps(
        {"concepts": [{"id": "x", "name": "X", "summary": "s", "pages": [2], "prerequisites": []}]}
    )
    llm = ScriptedLLM([bad, good])
    g = extract_graph(PAGES, llm)
    assert g.concepts[0].pages == [2]
    assert "pages [7]" in llm.prompts[1]  # the error was sent back to the model


def test_extract_accepts_code_fences_and_gives_up_eventually():
    fenced = "```json\n" + json.dumps({"concepts": [C("x", pages=[1]).model_dump()]}) + "\n```"
    assert extract_graph(PAGES, ScriptedLLM([fenced])).concepts[0].id == "x"
    with pytest.raises(ExtractionError):
        extract_graph(PAGES, ScriptedLLM(["not json"] * 3))


def test_prompt_wraps_slides_as_data():
    llm = ScriptedLLM([json.dumps({"concepts": [C("x").model_dump()]})])
    extract_graph(PAGES, llm)
    assert llm.prompts[0].startswith("<lecture_content>\n[p.1]\nintro text")


@pytest.mark.skipif(
    not (M04.exists() and M04_VISION.exists()), reason="M04 fixture files are not present locally"
)
def test_sample_answer_passes_checks_on_real_lecture():
    # Mirrors scripts/build_graph.py's real pipeline: merge pages + vision, then
    # only send page_type == "content" pages to the model (same as build_graph.py).
    pages = parse_pdf(str(M04))
    vision = json.loads(M04_VISION.read_text(encoding="utf-8"))
    records = merge(pages, vision)
    content_pages = [
        Page(page=r.page, slide_no=r.slide_no, title=r.title or "", text=r.rich_text, needs_vision=False)
        for r in records
        if r.page_type == "content" and r.rich_text
    ]

    g = extract_graph(content_pages, FileLLM(str(FIX / "sample_llm_answer_m04.json")))
    assert len(g.concepts) == 14
    gd = next(c for c in g.concepts if c.id == "gradient_descent")
    assert gd.prerequisites == ["cost_surface_convexity"]  # indirect edge removed


# ---------- evaluation ----------


def test_compare_graph():
    gold = [
        {"id": "gd", "name": "Gradient descent", "prerequisites": ["risk"]},
        {"id": "risk", "name": "Empirical risk", "prerequisites": []},
        {"id": "ne", "name": "Normal equation", "prerequisites": []},
    ]
    pred = [
        {"id": "gradient_descent", "name": "Gradient descent", "prerequisites": []},
        {"id": "empirical_risk", "name": "Empirical risk", "prerequisites": ["gradient_descent"]},
        {"id": "softmax", "name": "Softmax", "prerequisites": []},
    ]
    r = compare(pred, gold)
    assert r["missed"] == ["ne"] and r["extra"] == ["softmax"]
    assert r["edge_recall"] == 0.0
    assert r["edges_reversed"] == [("empirical_risk", "gradient_descent")]
