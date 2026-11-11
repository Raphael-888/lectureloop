"""Pure helpers for selected-concept review; no session or learning side effects."""

from .bkt import label_for
from .root_cause import _concept_id, _graph, _mastery, next_prerequisite


def _ids(values, adjacency, name):
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{name} must be a list or tuple of concept IDs")
    result = []
    for cid in values:
        _concept_id(cid)
        if cid not in adjacency:
            raise ValueError(f"Unknown concept: {cid}")
        if cid not in result:
            result.append(cid)
    return result


def _scores(mastery, adjacency):
    scores = _mastery(mastery)
    if scores.keys() - adjacency.keys():
        raise ValueError("Mastery contains concepts outside this graph")
    return scores


def review_scope(selected_ids, graph):
    """Validate and deduplicate explicit targets, preserving user selection order.

    An empty selection stays empty: it never silently selects the whole lecture.
    Prerequisites remain in the full graph but are not automatically quiz targets.
    """
    return _ids(selected_ids, _graph(graph), "selected_ids")


def review_progress(selected_ids, graph, mastery):
    """Return mastery counts for selected targets only, without mutating evidence.

    mastered_fraction is a concept count ratio, not a learning gain, monetary
    refund, or session completion decision. Empty scope has fraction None.
    """
    adjacency = _graph(graph)
    targets = _ids(selected_ids, adjacency, "selected_ids")
    scores = _scores(mastery, adjacency)
    counts = dict.fromkeys(("mastered", "confused", "not_mastered", "untested"), 0)
    for cid in targets:
        p = scores.get(cid)
        counts[label_for(p, tested=p is not None)] += 1
    return {
        "total": len(targets),
        "tested": len(targets) - counts["untested"],
        **counts,
        "mastered_fraction": counts["mastered"] / len(targets) if targets else None,
    }


def campfire_candidates(selected_ids, graph, mastery, marked_ids=()):
    """Return scoped practice candidates with separate evidence and self-report.

    Include tested weak concepts and explicitly marked concepts in selection
    order. An untested concept is not automatically weak. Marking a mastered
    concept is allowed and never lowers its probability. No automatic removal
    of user marks or persistence is performed here.
    """
    adjacency = _graph(graph)
    targets = _ids(selected_ids, adjacency, "selected_ids")
    marked = set(_ids(marked_ids, adjacency, "marked_ids"))
    scores = _scores(mastery, adjacency)
    candidates = []
    for cid in targets:
        p = scores.get(cid)
        label = label_for(p, tested=p is not None)
        reasons = []
        if cid in marked:
            reasons.append("self_reported")
        if label in {"confused", "not_mastered"}:
            reasons.append("tested_weak")
        if reasons:
            candidates.append({"concept_id": cid, "label": label, "reasons": reasons})
    return candidates


def prerequisite_check(concept_id, selected_ids, graph, mastery):
    """Describe the next diagnostic candidate without expanding the review scope.

    B decides whether to ask about an out-of-scope prerequisite. None means no
    unresolved direct prerequisite, never proof that concept_id is a root cause.
    """
    adjacency = _graph(graph)
    targets = _ids(selected_ids, adjacency, "selected_ids")
    _concept_id(concept_id)
    if concept_id not in targets:
        raise ValueError("Diagnostic target must be in the selected scope")
    candidate = next_prerequisite(concept_id, adjacency, mastery)
    if candidate is None:
        return None
    return {"concept_id": candidate, "outside_scope": candidate not in targets}
