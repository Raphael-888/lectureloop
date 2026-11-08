# Gold concept graphs (hand-written)

One JSON file per lecture, same shape as `graph.json`:
`{"concepts": [{"id", "name", "summary", "pages", "prerequisites"}]}`.

Write these **by hand, before looking at any LLM output**. They are the answer key
used by `eval/compare_graph.py`; an answer key copied from the model only measures
the model against itself.

Rules (same as the extraction prompt):
1. Each concept can be tested on its own with 1–2 questions; usually 8–15 per lecture.
2. A → B only if you cannot understand B without A. Direct prerequisites only.
3. Only concepts this lecture teaches. Pages are PDF page numbers (see `out/<lecture>/pages.md`).

Keep 1–2 lectures for final evaluation only: never use them while tuning the prompt.
