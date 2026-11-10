"""search_slides: keyword (BM25) retrieval over slide pages, plus citation checking.

One slide page is one chunk. This is the fallback until C's vector search
exists; keep the return shape (page, title, text, score) when swapping it in.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable

from app.models import Citation, SlidePage

_STOP = frozenset(
    "a an and are as at be by for from has have how in is it its of on or that the this to was "
    "what when which why with you your can not do does we they their".split()
)
SEARCHABLE = {"content", "quiz"}  # skip title, outcomes, outlook, references and blank pages
MAX_CHUNK_CHARS = 1800
MAX_QUOTE_CHARS = 240


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP and len(t) > 1]


def search_pages(pages: list[SlidePage], query: str, k: int = 3, prefer: Iterable[int] = ()) -> list[dict]:
    """Top-k pages for the query. Pages in `prefer` (the concept's own pages) rank first."""
    prefer = set(prefer)
    docs = [(p, tokenize(f"{p.title} {p.text}")) for p in pages if p.text and p.page_type in SEARCHABLE]
    if not docs:
        return []
    avg_len = sum(len(tokens) for _, tokens in docs) / len(docs)
    df = Counter(t for _, tokens in docs for t in set(tokens))
    terms = set(tokenize(query))

    scored = []
    for page, tokens in docs:
        tf = Counter(tokens)
        score = 0.0
        for t in terms:
            if t in tf:
                idf = math.log(1 + (len(docs) - df[t] + 0.5) / (df[t] + 0.5))
                score += idf * tf[t] * 2.5 / (tf[t] + 1.5 * (0.25 + 0.75 * len(tokens) / avg_len))
        if score > 0 or page.page in prefer:
            scored.append((score, page))
    # the concept's own pages always come first: they are where the slides teach it
    scored.sort(key=lambda sp: (sp[1].page not in prefer, -sp[0], sp[1].page))
    return [
        {"page": p.page, "title": p.title, "text": p.text[:MAX_CHUNK_CHARS], "score": round(s, 3)}
        for s, p in scored[:k]
    ]


def _squash(text: str) -> str:
    return " ".join(text.split())


def verify_quote(chunks: list[dict], page: object, quote: object) -> Citation | None:
    """Accept a model-written citation only if the quote really is on that page."""
    if not isinstance(page, int) or isinstance(page, bool) or not isinstance(quote, str):
        return None
    needle = _squash(quote).strip(" \"'“”‘’.…")
    if len(needle) < 8:
        return None
    for chunk in chunks:
        if chunk["page"] != page:
            continue
        hay = _squash(chunk["text"])
        at = hay.lower().find(needle.lower())
        if at >= 0:
            return Citation(page=page, quote=hay[at : at + len(needle)][:MAX_QUOTE_CHARS])
    return None


def best_line(chunks: list[dict], query: str) -> Citation | None:
    """Fallback citation: the slide line that shares the most words with the query."""
    terms = set(tokenize(query))
    best: tuple[float, int, str] | None = None
    for rank, chunk in enumerate(chunks):
        for line in chunk["text"].splitlines():
            line = _squash(line)
            if len(line) < 20:
                continue
            words = set(tokenize(line))
            score = len(words & terms) / math.sqrt(len(words) + 1) - 0.01 * rank
            if best is None or score > best[0]:
                best = (score, chunk["page"], line)
    if best is None:
        return None
    return Citation(page=best[1], quote=best[2][:MAX_QUOTE_CHARS])
