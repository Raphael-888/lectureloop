# API contract

Owner: B (backend). Reviewed by: A (frontend). Status: **implemented in `backend/app/main.py`**.
Change this file in the same pull request as any change to the routes or bodies.

Base URL: `/api`. All bodies are JSON unless noted. Every error, whatever the status code, uses:

```json
{ "error": { "code": "lecture_not_found", "message": "No lecture with id l_123" } }
```

## Shared objects

```json
// Concept. "id" is a snake_case slug chosen by the extractor (C), unique within the lecture.
{ "id": "gradient_descent", "name": "Gradient descent and the update rule",
  "summary": "Repeatedly move the weights against the gradient of the cost.",
  "pages": [17, 19], "prerequisites": ["cost_surface_convexity"] }
// prerequisites: DIRECT prerequisites only, always ids of concepts in the same lecture

// Question (the answer key is never sent)
{ "id": "q_3f9a1c20b7de", "concept_id": "gradient_descent", "type": "multiple_choice",
  "prompt": "What does the learning rate control?",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."] }
// type: "multiple_choice" | "short_answer"; short_answer has no "options" key

// Mastery (probability from BKT, 0–1) and label
{ "concept_id": "gradient_descent", "p_mastery": 0.646, "label": "confused" }
// label: "mastered" (p >= 0.8) | "confused" (0.5 <= p < 0.8) | "not_mastered" (p < 0.5) | "untested"
// An untested concept reports the BKT prior (0.30) with label "untested".
// Thresholds and the prior live in backend/app/learner/bkt.py (D).

// Trace event (shown in the agent trace panel)
{ "step": 7, "time": "2026-11-10T14:03:22Z", "tool": "trace_root_cause",
  "reason": "Gradient descent answered wrong; check whether a prerequisite is the real gap",
  "summary": "Unresolved prerequisite of Gradient descent: Cost surface and convexity (untested)" }
// tool: "extract_concepts" | "generate_quiz" | "grade_answer" | "update_mastery" |
//       "trace_root_cause" | "search_slides" | "explain" | "export_flashcards"
// step starts at 1 and has no gaps. "reason" is why the agent made the call; when the model
// chose the step, it is the model's own one-sentence reason.
```

## 1. Upload a lecture

`POST /api/lectures` — `multipart/form-data` with field `file` (PDF only, max 25 MB).

```json
// 202 Accepted
{ "lecture_id": "l_29564dcb37e0fb3b", "status": "processing" }
```

Errors: `413 file_too_large`, `415 unsupported_file_type` (wrong extension or not a PDF inside),
`503 llm_not_configured`. The uploaded file is deleted once its text has been extracted.

## 2. Get concepts (for the mastery map)

`GET /api/lectures/{lecture_id}/concepts`

```json
{ "lecture_id": "l_29564dcb37e0fb3b", "status": "ready", "error": null,
  "concepts": [ /* Concept */ ] }
// status: "processing" | "ready" | "failed" — frontend polls until "ready" or "failed"
// error: a message for the student when status is "failed", otherwise null
```

Errors: `404 lecture_not_found`.

## 3. Start a review session

`POST /api/sessions`

```json
// request
{ "lecture_id": "l_29564dcb37e0fb3b" }
// response
{ "session_id": "s_8fd2abd481e998097e593e3b", "questions": [ /* exactly one Question */ ] }
```

Errors: `404 lecture_not_found`, `409 lecture_not_ready`.

## 4. Submit an answer

`POST /api/answers`

```json
// request. answer: the option letter for multiple_choice ("B"), free text for short_answer (max 4000 chars)
{ "session_id": "s_8fd2...", "question_id": "q_3f9a1c20b7de", "answer": "B" }
// response
{ "correct": false,
  "concept_id": "gradient_descent",
  "feedback": "You described the learning rate as the direction of the step, but ...",
  "citation": { "page": 17, "quote": "scaled by a learning rate" },
  "mastery": [ /* Mastery for every concept */ ],
  "next_action": "explain",
  "next_questions": [ /* one Question, or empty when next_action is "done" */ ] }
```

| `next_action` | Meaning | `next_questions[0]` is about |
| --- | --- | --- |
| `next_question` | Nothing to diagnose: confirm this concept, return to a waiting one, or cover a new one | any concept |
| `test_prerequisite` | Tracing a root cause: checking a prerequisite before re-explaining | a prerequisite of a concept the student got wrong |
| `explain` | `feedback` is an explanation of the root-cause concept and `citation` points at the slide | the explained concept (re-test), or another concept if its attempts ran out |
| `done` | Every concept is mastered or out of attempts; notes are ready | — |

- `citation` is present only with an explanation. `quote` is always text that appears on that page.
- Only the question most recently handed out can be answered.
- Sending the same answer again (for example after a network retry) returns the same response and
  does not update mastery twice.

Errors: `404 session_not_found`, `404 question_not_found`, `409 question_not_active`,
`422 invalid_request`.

## 5. Agent trace

`GET /api/sessions/{session_id}/trace?after_step=6` → `{ "events": [ /* Trace event */ ] }`

Returns events with `step > after_step` (default 0), oldest first. The frontend polls this.

## 6. Notes and flashcards

`GET /api/sessions/{session_id}/notes`

```json
{ "summary_markdown": "# Lecture title: review notes ...",
  "weak_concepts": ["cost_surface_convexity", "gradient_descent"],
  "flashcards": [ { "front": "...", "back": "...", "concept_id": "gradient_descent", "page": 17 } ] }
// weak_concepts: answered wrong at least once, or tested and still below 0.8; weakest first
// flashcards: the questions the student missed, then one card per concept (weak concepts first)
```

`GET /api/sessions/{session_id}/flashcards.csv` → two columns (front, back), no header. Import in
Anki with File > Import.

Both work at any point in a session, not only after `done`.

## 7. Evaluation and health (not used by the frontend)

`GET /api/sessions/{session_id}/log` → every graded answer (concept, correct, mastery before and
after, `next_action`, latency), the diagnosed `root_causes` (`symptom`, `root`, trace `step`),
final mastery, lecture processing times, and model usage per tool. D uses this for the metrics.

`GET /api/health` → `{ "status": "ok", "llm": "deepseek", "planner": "llm" }`

## Internal interfaces (backend modules)

| Function | Owner | Where | Notes |
| --- | --- | --- | --- |
| `bkt_update(p, correct, params)`, `params_for(question_type)`, `label_for(p, tested)` | D | `app/learner/bkt.py` | one update per answer; `p=None` starts from the prior |
| `next_prerequisite(concept_id, graph, mastery)` | D | `app/learner/root_cause.py` | first unresolved direct prerequisite, or `None` |
| `parse_pdf`, `merge`, `extract_graph(pages, llm)` | C | `app/retrieval/`, `app/concepts/` | called by `app/pipeline.py` after an upload |
| `search_pages(pages, query, k, prefer)` | B (fallback) | `app/agent/search.py` | keyword BM25; replace with C's vector search, same return shape |
| `build_notes(lecture, session)`, `flashcards_csv(notes)` | B (fallback) | `app/output/notes.py` | built from stored data, no model call |

## Decisions (were open on Nov 2)

- **Agent framework**: hand-written loop (`app/agent/loop.py`), no LangGraph: one file that is
  easy to debug and to explain in the pitch.
- **LLM provider**: any of `anthropic`, `openai`, `deepseek` through `LLM_PROVIDER` / `LLM_MODEL` /
  `LLM_API_KEY`, using C's client in `app/llm.py`.
- **Polling, not streaming**: the frontend polls concepts and trace. Streaming is first on the cut list.
- **BKT parameters**: fixed defaults per question type (`params_for`), not per concept.
- **Storage**: SQLite file for the MVP (`app/store.py`); PostgreSQL + pgvector is future work.
