"""Compare an extracted concept graph with a hand-written gold graph.

Usage (run from backend/):
  python eval/compare_graph.py out/cs3151_m04/graph.json tests/fixtures/gold/cs3151_m04.json

Concepts are matched by name similarity (then id). Check the printed matches by
eye: a wrong automatic match makes the numbers look better than they are.
"""

import json
import sys
from difflib import SequenceMatcher

THRESHOLD = 0.6


def _norm(s: str) -> str:
    return " ".join(s.lower().replace("_", " ").replace("-", " ").split())


def _sim(a: dict, b: dict) -> float:
    return max(
        SequenceMatcher(None, _norm(a["name"]), _norm(b["name"])).ratio(),
        SequenceMatcher(None, _norm(a["id"]), _norm(b["id"])).ratio(),
    )


def match(pred: list[dict], gold: list[dict]) -> dict[str, str]:
    """Greedy one-to-one matching, best pairs first. Returns {gold_id: pred_id}."""
    pairs = sorted(((_sim(p, g), g["id"], p["id"]) for p in pred for g in gold), reverse=True)
    used_g, used_p, m = set(), set(), {}
    for s, gid, pid in pairs:
        if s < THRESHOLD:
            break
        if gid not in used_g and pid not in used_p:
            m[gid] = pid
            used_g.add(gid)
            used_p.add(pid)
    return m


def edges(concepts: list[dict]) -> set[tuple[str, str]]:
    return {(pre, c["id"]) for c in concepts for pre in c.get("prerequisites", [])}


def compare(pred: list[dict], gold: list[dict]) -> dict:
    m = match(pred, gold)
    g2p = m
    gold_edges = edges(gold)
    pred_edges = edges(pred)
    # gold edges whose both ends were matched, translated into predicted ids
    comparable = {(g2p[a], g2p[b]) for a, b in gold_edges if a in g2p and b in g2p}
    reversed_ = {(a, b) for a, b in comparable if (b, a) in pred_edges}
    return {
        "matches": m,
        "missed": [g["id"] for g in gold if g["id"] not in m],
        "extra": [p["id"] for p in pred if p["id"] not in m.values()],
        "concept_recall": len(m) / len(gold) if gold else 0.0,
        "concept_precision": len(m) / len(pred) if pred else 0.0,
        "edge_recall": len(comparable & pred_edges) / len(comparable) if comparable else 0.0,
        "edges_reversed": sorted(reversed_),
    }


def main() -> None:
    with open(sys.argv[1], encoding="utf-8") as f:
        pred = json.load(f)["concepts"]
    with open(sys.argv[2], encoding="utf-8") as f:
        gold = json.load(f)["concepts"]
    r = compare(pred, gold)
    print("matches (gold -> extracted):")
    for g, p in r["matches"].items():
        print(f"  {g:35s} -> {p}")
    print(f"missed : {r['missed']}")
    print(f"extra  : {r['extra']}")
    print(f"concept recall    {r['concept_recall']:.0%}")
    print(f"concept precision {r['concept_precision']:.0%}")
    print(f"edge recall       {r['edge_recall']:.0%}  (among edges whose two concepts were both found)")
    if r["edges_reversed"]:
        print(f"edges pointing the wrong way: {r['edges_reversed']}")


if __name__ == "__main__":
    main()
