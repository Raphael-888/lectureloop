"""Select a diagnostic question, never assert a proven causal explanation."""

from collections import deque
from collections.abc import Mapping

from .bkt import MASTERY_THRESHOLD, _probability, label_for


def _concept_id(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Concept IDs must be nonempty strings")
    return value


def _graph(graph):
    # C's Pydantic ConceptGraph works directly or via model_dump().
    if callable(getattr(graph, "model_dump", None)):
        graph = graph.model_dump()
    if isinstance(graph, Mapping) and isinstance(graph.get("concepts"), list):
        graph = graph["concepts"]
    if isinstance(graph, list):
        adjacency = {}
        for concept in graph:
            if not isinstance(concept, Mapping) or "id" not in concept:
                raise ValueError("Each Concept must contain id")
            cid = _concept_id(concept["id"])
            if cid in adjacency:
                raise ValueError(f"Duplicate concept: {cid}")
            adjacency[cid] = concept.get("prerequisites", [])
    elif isinstance(graph, Mapping):
        adjacency = dict(graph)
    else:
        raise ValueError(
            "graph must be adjacency mapping, Concept list or ConceptGraph"
        )
    for cid, parents in adjacency.items():
        _concept_id(cid)
        if not isinstance(parents, (list, tuple)):
            raise ValueError("prerequisites must be a list or tuple")
        seen = set()
        for parent in parents:
            _concept_id(parent)
            if parent not in adjacency:
                raise ValueError(f"Unknown prerequisite: {parent}")
            if parent in seen:
                raise ValueError(f"Duplicate prerequisite: {parent}")
            seen.add(parent)
    # Iterative topological validation is safe even for deep graphs.
    pending = {cid: len(parents) for cid, parents in adjacency.items()}
    children = {cid: [] for cid in adjacency}
    for cid, parents in adjacency.items():
        for parent in parents:
            children[parent].append(cid)
    ready = deque(cid for cid, count in pending.items() if count == 0)
    count = 0
    while ready:
        cid = ready.popleft()
        count += 1
        for child in children[cid]:
            pending[child] -= 1
            if pending[child] == 0:
                ready.append(child)
    if count != len(adjacency):
        raise ValueError("Concept graph contains a cycle")
    return adjacency


def _mastery(mastery):
    if isinstance(mastery, list):
        records = {}
        for record in mastery:
            if not isinstance(record, Mapping) or "concept_id" not in record:
                raise ValueError("Mastery record requires concept_id")
            cid = _concept_id(record["concept_id"])
            if cid in records:
                raise ValueError(f"Duplicate mastery: {cid}")
            records[cid] = record
        mastery = records
    if not isinstance(mastery, Mapping):
        raise ValueError("mastery must be a mapping or list of Mastery records")
    result = {}
    for cid, value in mastery.items():
        _concept_id(cid)
        if isinstance(value, Mapping):
            if "concept_id" in value and value["concept_id"] != cid:
                raise ValueError("Mastery concept_id does not match its key")
            label = value.get("label")
            if not isinstance(label, str) or label not in {
                "mastered",
                "confused",
                "not_mastered",
                "untested",
            }:
                raise ValueError("Mastery record requires a valid label")
            p = value.get("p_mastery")
            tested = label != "untested"
            if label_for(p, tested=tested) != label:
                raise ValueError("Mastery label disagrees with p_mastery thresholds")
            result[cid] = p if tested else None
        else:
            result[cid] = None if value is None else _probability(value, "p_mastery")
    return result


def next_prerequisite(concept_id, graph, mastery):
    """Return first unresolved DIRECT prerequisite in graph order, else None.

    Accepts original adjacency/probability mappings, API Concept/Mastery lists
    and C's ConceptGraph. Missing mastery, None or untested needs testing even
    with a high prior. A tested score below 0.8 remains a hypothesis.
    None means no unresolved direct prerequisite, NOT a proven root cause.
    B controls testing, explanation, traversal and retry limits; re-call with
    the returned concept to inspect another level after obtaining evidence.
    All nodes, including leaves, must be explicit. Invalid data raises ValueError.
    """
    _concept_id(concept_id)
    adjacency = _graph(graph)
    if concept_id not in adjacency:
        raise ValueError(f"Unknown concept: {concept_id}")
    scores = _mastery(mastery)
    if scores.keys() - adjacency.keys():
        raise ValueError("Mastery contains concepts outside this graph")
    for parent in adjacency[concept_id]:
        p = scores.get(parent)
        if p is None or p < MASTERY_THRESHOLD:
            return parent
    return None
