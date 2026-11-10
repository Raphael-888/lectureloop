# Backend (FastAPI + agent)

Owners: B (agent, API), C (retrieval, data, output), D (BKT model, root-cause rules).

## Run it

Requires Python 3.11+.

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env             # then set LLM_PROVIDER, LLM_MODEL, LLM_API_KEY
uvicorn app.main:app --reload    # http://localhost:8000, interactive docs at /docs
pytest -q                        # no API key or network needed
```

No API key? Set `LLM_PROVIDER=offline` in `.env`. A rule-based stand-in replaces the model, so the
whole flow runs for free. Its concepts and questions are crude: use it for frontend integration and
tests, never for a demo.

To use it with the frontend: in `frontend/.env.local` set `NEXT_PUBLIC_USE_MOCK=false`.

## Layout

```
backend/
  app/
    main.py          FastAPI routes (docs/api-contract.md) and the error envelope      B
    pipeline.py      background job per upload: parse -> concept graph -> questions    B
    store.py         SQLite: lectures, question bank, sessions, evaluation logs        B
    models.py        API bodies and stored lecture/session state                       B
    agent/
      loop.py        the agent loop: one turn per answer, writes the trace             B
      planner.py     the model picks the next tool call                                B
      policy.py      guardrails: valid tool calls + the deterministic default          B
      quiz.py  grading.py  explain.py  search.py     the tools                         B
      llm.py         JSON calls, usage logging         offline_llm.py  no-key stand-in B
    concepts/        concept-graph extraction and checks                               C
    retrieval/       PDF parsing, page types, vision merge                             C
    learner/         BKT mastery model, root-cause rule                                D
    output/notes.py  notes, flashcards, Anki CSV                                       B (fallback for C)
  tests/
  .env.example       copy to .env and add your own keys (never commit .env)
```

## How the agent works

After an upload, `pipeline.py` parses the PDF, asks the model for the concept graph (C's
`extract_graph`, validated in code) and starts filling a question bank in the background. The
lecture is usable as soon as the graph exists; a question that is not in the bank yet is generated
on demand.

A session starts with the most advanced concept, so a gap can be traced backwards. Then, for every
answer (`agent/loop.py`):

1. `grade_answer`: multiple choice by answer key; short answer by the model against a rubric.
2. `update_mastery`: D's BKT update for that concept.
3. The **planner** (`agent/planner.py`) reads the learner state (mastery, attempts left, what is
   waiting on a prerequisite check, what the tools returned so far this turn) and picks the next
   tool call. This repeats until a call ends the turn:
   - `trace_root_cause(concept)`: D's rule returns the first prerequisite the student has not
     shown they know. None left means this concept is the likely root cause.
   - `explain(concept)`: runs `search_slides`, then writes an explanation with a slide citation.
   - `generate_quiz(concept)`: hands the student one new question. Ends the turn.
   - `finish`: builds notes and flashcards. Ends the session.

Every call is appended to the session trace with the reason for it, which is what the trace panel
shows.

### Guardrails

The model only ever chooses from a list of valid calls computed by `agent/policy.py`, so it cannot
skip a step or do anything else, whatever the slides or the student's answer say:

- a wrong answer is always traced before anything else;
- a concept is re-tested only after an explanation, and at most `MAX_ATTEMPTS_PER_CONCEPT` times;
- the session cannot finish while any concept is neither mastered nor out of attempts, so every
  concept is covered and the loop always terminates.

If the model times out, replies with invalid JSON or picks something not on the list, the loop uses
the deterministic default from the same file. `AGENT_PLANNER=rules` turns the model planner off
entirely (faster, and useful as a baseline when measuring what the planner adds). With no model at
all the agent still runs: answer keys, a keyword grader and slide lines stand in for the model.

## Security

- **Prompt injection**: slide text and student answers reach the model only as values inside a JSON
  payload, and every system prompt declares them as data (`agent/llm.py: UNTRUSTED`). Model output
  is never executed or trusted: the planner's answer is an index into a server-built list, generated
  questions are schema-checked (`quiz._to_item`), and a citation is accepted only if the quote is
  really on that page (`search.verify_quote`), otherwise a real slide line replaces it.
- **Uploads**: size limit, `.pdf` extension and PDF magic bytes are checked before anything is
  stored; the file name is never used as a path; the file is deleted after its text is extracted.
- **Answer keys** stay on the server (`QuestionItem.public()`).
- **Errors** never include stack traces. Ids are random tokens, since there are no user accounts.
- **Secrets** only in `backend/.env`, which is git-ignored.

Known limits of the MVP: no authentication or rate limiting, and one server process (the per-session
lock in `store.py` is in memory; moving to PostgreSQL row locks removes that limit).

## Evaluation data

Every graded answer and every model call is logged in SQLite (`answer_log`, `llm_log`).
`GET /api/sessions/{id}/log` returns one session's answers, diagnosed root causes, mastery, lecture
processing times (`ready_s` is upload to concept graph ready) and model usage per tool.

`tests/test_agent_units.py::test_planted_gap_is_diagnosed_as_the_only_root_cause` plants a gap at
each of the 15 concepts of C's gold graph for CSCI 3151 M04 in turn and checks that the agent names
exactly that concept as the root cause.

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
