# Backend (FastAPI + agent)

Owners: B (agent, API), C (retrieval, data, output), D (BKT model, root-cause rules).

Planned layout:

```
backend/
  app/
    main.py          FastAPI app and routes (see docs/api-contract.md)
    agent/           agent loop and tools
    retrieval/       PDF parsing, chunking, vector search
    learner/         BKT mastery model, root-cause rules
    output/          notes, flashcards, Anki export
  tests/
  .env.example       copy to .env and add your own keys (never commit .env)
```

Setup instructions will be added on Nov 2–3.

## Concept graph: PDF → knowledge graph (C)

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env            # set LLM_PROVIDER, LLM_MODEL, LLM_API_KEY, then export them

# 1. PDF text layer + vision-model JSON -> one record per page
python scripts/parse_lecture.py tests/fixtures/lectures/cs3151_m04.pdf \
  --vision tests/fixtures/lectures/cs3151_m04.vision.json
#   out/cs3151_m04/pages.md    cleaned text per page (check parsing, write gold graphs)
#   out/cs3151_m04/pages.json  PageRecord list, fed to build_graph.py

# 2. pages.json -> concept graph (only page_type == "content" pages are sent to the LLM)
python scripts/build_graph.py out/cs3151_m04/pages.json
#   out/cs3151_m04/graph.json  concept graph (docs/api-contract.md Concept shape + summary)
#   out/cs3151_m04/graph.md    Mermaid diagram
#   out/cs3151_m04/raw/        every raw LLM reply, cached by (pages.json hash, prompt_version, model)

python eval/compare_graph.py out/cs3151_m04/graph.json tests/fixtures/gold/cs3151_m04.json
pytest -q
```

No API key yet? `--llm-file tests/fixtures/sample_llm_answer_m04.json` runs `build_graph.py`
offline with a saved answer.

How it works: parse pages (merge PDF text layer + vision reading, classify page type) → one
LLM call drafts the whole graph from the content pages → code checks ids, pages, missing
prerequisites and cycles → on failure the errors are sent back for up to 2 retries → indirect
edges are removed so root-cause tracing goes one level at a time.

Lecture PDFs and vision-model transcripts are course material and are not committed: put
them in `tests/fixtures/lectures/` locally.

Current extraction prompt: `extract_v2` (see `app/concepts/extract.py`).
