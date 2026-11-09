import copy

import pytest
from app.learner.root_cause import next_prerequisite

GRAPH = {"target": ["a", "b"], "a": [], "b": ["base"], "base": []}


@pytest.mark.parametrize(
    "mastery,expected",
    [
        ({}, "a"),
        ({"a": None}, "a"),
        ({"a": 0.79}, "a"),
        ({"a": 0.8}, "b"),
        ({"a": 1, "b": 0.2}, "b"),
        ({"a": 0.8, "b": 0.8}, None),
    ],
)
def test_multiple_prerequisites(mastery, expected):
    assert next_prerequisite("target", GRAPH, mastery) == expected


def test_leaves_and_one_level_at_a_time():
    assert next_prerequisite("base", GRAPH, {}) is None
    assert next_prerequisite("target", GRAPH, {"a": 1, "b": 0.2}) == "b"
    assert next_prerequisite("b", GRAPH, {"b": 0.2}) == "base"
    # Even here None is only a lack of unresolved prerequisites, not causal proof.
    assert next_prerequisite("target", GRAPH, {"a": 1, "b": 1, "base": 0}) is None


@pytest.mark.parametrize("wrapped", [False, True])
def test_contract_json_and_untested_high_prior(wrapped):
    concepts = [
        {"id": cid, "name": cid, "pages": [1], "prerequisites": parents}
        for cid, parents in GRAPH.items()
    ]
    graph = {"lecture_id": "l1", "concepts": concepts} if wrapped else concepts
    mastery = [{"concept_id": "a", "p_mastery": 0.99, "label": "untested"}]
    assert next_prerequisite("target", graph, mastery) == "a"
    mastery[0]["label"] = "mastered"
    assert next_prerequisite("target", graph, mastery) == "b"
    mastery.append({"concept_id": "b", "p_mastery": 0.6, "label": "confused"})
    assert next_prerequisite("target", graph, mastery) == "b"
    assert (
        next_prerequisite("target", graph, {r["concept_id"]: r for r in mastery}) == "b"
    )


@pytest.mark.parametrize(
    "graph",
    [
        None,
        [],
        {},
        {"a": "b"},
        {"a": ["missing"]},
        {"a": ["a"]},
        {"a": ["b"], "b": ["a"]},
        {"a": ["b", "b"], "b": []},
        [{"id": "a"}, {"id": "a"}],
        [{"name": "a"}],
        {"a": [None]},
        {"": []},
    ],
)
def test_invalid_graph(graph):
    with pytest.raises(ValueError):
        next_prerequisite("a", graph, {})


@pytest.mark.parametrize(
    "mastery",
    [
        None,
        "bad",
        {"a": -1},
        {"a": float("nan")},
        {"a": True},
        {"missing": 0.4},
        [{}],
        [{"concept_id": "a"}, {"concept_id": "a"}],
        {"a": {"concept_id": "b", "p_mastery": 0.5, "label": "confused"}},
        {"a": {"p_mastery": 0.35, "label": "confused"}},
        {"a": {"label": "mastered"}},
        {"a": {"label": []}},
        {"a": {"p_mastery": 2, "label": "untested"}},
    ],
)
def test_invalid_mastery(mastery):
    with pytest.raises(ValueError):
        next_prerequisite("target", GRAPH, mastery)


@pytest.mark.parametrize("cid", ["unknown", "", None, []])
def test_invalid_target(cid):
    with pytest.raises(ValueError):
        next_prerequisite(cid, GRAPH, {})


def test_no_mutation_and_stable_order():
    graph = copy.deepcopy(GRAPH)
    mastery = {"a": 0.7, "b": 0.1}
    before = copy.deepcopy((graph, mastery))
    assert next_prerequisite("target", graph, mastery) == "a"
    assert (graph, mastery) == before


def test_deep_graph_without_recursion():
    graph = {str(i): [str(i + 1)] for i in range(2000)}
    graph["2000"] = []
    assert next_prerequisite("0", graph, {}) == "1"
    graph["2000"] = ["0"]
    with pytest.raises(ValueError, match="cycle"):
        next_prerequisite("0", graph, {})


def test_disconnected_cycle_is_invalid():
    with pytest.raises(ValueError, match="cycle"):
        next_prerequisite("leaf", {"leaf": [], "x": ["y"], "y": ["x"]}, {})
