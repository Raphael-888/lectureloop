"""Deterministic checks on a concept graph. No LLM here."""

import networkx as nx

from app.schemas import ConceptGraph


def check_graph(g: ConceptGraph, valid_pages: set[int]) -> list[str]:
    """Return a list of human-readable problems. Empty list = graph is OK."""
    errors: list[str] = []
    ids = [c.id for c in g.concepts]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        errors.append(f"duplicate ids: {dup}")
    if not g.concepts:
        errors.append("no concepts")

    idset = set(ids)
    G = nx.DiGraph()
    G.add_nodes_from(idset)
    for c in g.concepts:
        bad_pages = [p for p in c.pages if p not in valid_pages]
        if bad_pages:
            errors.append(f"{c.id}: pages {bad_pages} are not pages of this lecture")
        for pre in c.prerequisites:
            if pre == c.id:
                errors.append(f"{c.id}: cannot be its own prerequisite")
            elif pre not in idset:
                errors.append(f"{c.id}: prerequisite '{pre}' does not exist")
            else:
                G.add_edge(pre, c.id)
    try:
        cycle = nx.find_cycle(G)
        errors.append("cycle: " + " -> ".join([u for u, _ in cycle] + [cycle[0][0]]))
    except nx.NetworkXNoCycle:
        pass
    return errors


def reduce_edges(g: ConceptGraph) -> ConceptGraph:
    """Drop indirect edges: with A->B->C, remove A->C so root-cause tracing goes one level at a time."""
    G = nx.DiGraph([(p, c.id) for c in g.concepts for p in c.prerequisites])
    G.add_nodes_from(c.id for c in g.concepts)
    R = nx.transitive_reduction(G)
    out = g.model_copy(deep=True)
    for c in out.concepts:
        c.prerequisites = sorted(R.predecessors(c.id))
    return out


def to_mermaid(g: ConceptGraph) -> str:
    """Mermaid flowchart; renders directly on GitHub."""
    lines = ["flowchart LR"]
    for c in g.concepts:
        label = f"{c.name}<br/>p.{','.join(map(str, c.pages))}".replace('"', "'")
        lines.append(f'    {c.id}["{label}"]')
    for c in g.concepts:
        for pre in c.prerequisites:
            lines.append(f"    {pre} --> {c.id}")
    return "\n".join(lines)
