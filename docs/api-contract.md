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
// tool: "extract_concepts" | "review_scope" | "summarize" | "generate_quiz" | "grade_answer" |
//       "update_mastery" | "trace_root_cause" | "search_slides" | "explain" | "chat" | "export_flashcards"
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

## 2. Get concepts (overview page and concept map)

`GET /api/lectures/{lecture_id}/concepts`

```json
{ "lecture_id": "l_29564dcb37e0fb3b", "status": "ready", "error": null,
  "title": "M04 Linear Regression", "page_count": 32,
  "overview": "## markdown ...",
  "concepts": [ /* Concept */ ] }
// status: "processing" | "ready" | "failed" — frontend polls until "ready" or "failed"
// error: a message for the student when status is "failed", otherwise null
// overview: Markdown summary of the whole lecture (one paragraph + one bullet per concept),
//           empty until status is "ready"
```

Errors: `404 lecture_not_found`.

## 2b. Slide pages (the "original PDF" view)

`GET /api/lectures/{lecture_id}/pages?concept_ids=gradient_descent,normal_equation`

```json
{ "lecture_id": "l_29564dcb37e0fb3b",
  "pages": [ { "page": 17, "title": "Gradient descent", "page_type": "content",
               "text": "the page's text layer (first 1200 characters)",
               "concept_ids": ["gradient_descent"] } ] }
// concept_ids (comma-separated) keeps only the pages that teach those concepts; omit it for all pages
```

Errors: `404 lecture_not_found`, `409 lecture_not_ready`. Page images are not served yet (the
PDF is deleted after parsing); the frontend renders each page from its text.

## 3. Start a review session

`POST /api/sessions`

```json
// request. concept_ids: what the student dragged into the review box (any order, duplicates
// ignored). Omitted or empty = review the whole lecture.
{ "lecture_id": "l_29564dcb37e0fb3b", "concept_ids": ["cost_surface_convexity", "gradient_descent"] }
// response
{ "session_id": "s_8fd2abd481e998097e593e3b", "questions": [ /* exactly one Question */ ] }
```

The session is **scoped** to `concept_ids` (D's `review_scope`): coverage, confirmation
questions and the end of the session look only at those concepts. Root-cause tracing may still ask
about a prerequisite *outside* the selection when the student gets a selected concept wrong, because
that is usually where the gap is; the trace says "outside the selection" and the UI shows it as a
prerequisite check. Mastery (`mastery` in every answer) is still reported for every concept.

Starting a session also writes `scope_summary` (section 3b) with one model call, so this request
takes a few seconds with a real model.

Errors: `404 lecture_not_found`, `409 lecture_not_ready`, `422 unknown_concept`.

## 3b. Session state (reload-safe)

`GET /api/sessions/{session_id}`

```json
{ "session_id": "s_8fd2...", "lecture_id": "l_2956...",
  "concept_ids": ["cost_surface_convexity", "gradient_descent"],
  "scope_summary": "markdown: one paragraph + one bullet per selected concept",
  "preferences": { "question_type": null, "difficulty": "same" },
  "chat": [ { "role": "student", "text": "...", "time": "..." }, { "role": "tutor", "text": "...", "time": "..." } ],
  "current_question": { /* Question */ },   // null once the session is done
  "mastery": [ /* Mastery for every concept */ ],
  "answered": 3, "done": false }
```

The pick-concepts page shows `scope_summary` and the chat; the quiz page loads
`current_question` from here, so a page refresh never loses the question.

## 3c. Tutor chat

`POST /api/sessions/{session_id}/chat`

```json
// request
{ "message": "Give me short answer questions instead, and make them harder" }
// response
{ "reply": "Got it. From the next question on you'll get open (short-answer) questions. The next questions will be harder ...",
  "preferences": { "question_type": "short_answer", "difficulty": "harder" },
  "changed": ["question_type", "difficulty"] }
```

One box, two jobs: a question about the material is answered from the slides (with a page
reference, e.g. "p. 17"); an instruction about the quiz updates `preferences` and `changed` lists
what moved. `question_type` is `"multiple_choice"`, `"short_answer"` or `null` (the agent decides:
multiple choice first, short answer to confirm). `difficulty` is `"easier"`, `"same"` or
`"harder"` and applies to questions generated from then on. Chatting never grades anything and
never changes mastery. Every exchange is appended to the trace (`tool: "chat"`).

Errors: `404 session_not_found`, `422 invalid_request`.

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
// flashcards: the questions the student missed, then one card per reviewed concept (weak first)
// In a scoped session (concept_ids) the notes cover the selected concepts plus any prerequisite
// the agent tested on the way; the section is titled "What you reviewed" instead of "All concepts".
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
| `review_scope(selected_ids, graph)` | D | `app/learner/review.py` | validates and deduplicates the student's selection |
| `chat(asker, lecture, session, message)` | A/B | `app/agent/chat.py` | tutor reply from the slides + preference changes; rule fallback without a model |
| `summarize(asker, lecture, concepts)` | A/B | `app/agent/summarize.py` | Markdown summary of some concepts; composed from the graph without a model |
| `search_pages(pages, query, k, prefer)` | B (fallback) | `app/agent/search.py` | keyword BM25; replace with C's vector search, same return shape |
| `build_notes(lecture, session)`, `flashcards_csv(notes)` | B (fallback) | `app/output/notes.py` | built from stored data, no model call |

## Decisions (Nov 10 meeting: selected-concept review)

- **Scope**: the student picks one or more concepts (drag and drop) and the session quizzes only
  those. Empty selection = whole lecture, so the original flow still works.
- **Prerequisites outside the selection may be tested** when a selected concept is answered wrong
  (A/B decision asked for in D's `REVIEW_INTEGRATION.md`). The alternative, staying inside the
  selection, would make the root-cause loop pointless for a single selected concept.
- **Question type and difficulty are set through the chat**, not with buttons; the agent decides
  by default. "Proof" and "calculation" requests map to `short_answer` at `harder` difficulty
  (D: no new question types without an agreed rubric).
- **Agent trace is hidden by default** in the UI (collapsed panel), still recorded and served, so
  the "visible agentic behaviour" judging criterion can be shown on demand.

## Decisions (were open on Nov 2)

- **Agent framework**: hand-written loop (`app/agent/loop.py`), no LangGraph: one file that is
  easy to debug and to explain in the pitch.
- **LLM provider**: any of `anthropic`, `openai`, `deepseek` through `LLM_PROVIDER` / `LLM_MODEL` /
  `LLM_API_KEY`, using C's client in `app/llm.py`.
- **Polling, not streaming**: the frontend polls concepts and trace. Streaming is first on the cut list.
- **BKT parameters**: fixed defaults per question type (`params_for`), not per concept.
- **Storage**: SQLite file for the MVP (`app/store.py`); PostgreSQL + pgvector is future work.
