# API contract (draft for the Nov 2 kickoff)

Owner: B (backend). Reviewed by: A (frontend). Status: **draft — discuss and freeze on Nov 2**.

Base URL: `/api`. All bodies are JSON unless noted. Errors use:

```json
{ "error": { "code": "lecture_not_found", "message": "No lecture with id l_123" } }
```

## Shared objects

```json
// Concept
{ "id": "c2", "name": "Memoization vs bottom-up", "pages": [12, 14], "prerequisites": ["c1"] }

// Question
{ "id": "q3", "concept_id": "c2", "type": "multiple_choice",
  "prompt": "Which approach fills the table from the smallest subproblem?",
  "options": ["A. Memoization", "B. Bottom-up", "C. Greedy", "D. Divide and conquer"] }
// type: "multiple_choice" | "short_answer"; short_answer has no "options"

// Mastery (probability from BKT, 0–1) and label
{ "concept_id": "c2", "p_mastery": 0.35, "label": "confused" }
// label: "mastered" | "confused" | "not_mastered" | "untested"

// Trace event (shown in the agent trace panel)
{ "step": 7, "time": "2026-11-10T14:03:22Z", "tool": "trace_root_cause",
  "reason": "c2 below threshold; testing prerequisite c1", "summary": "Generated 1 question on c1" }
```

## 1. Upload a lecture

`POST /api/lectures` — `multipart/form-data` with field `file` (PDF only, max 25 MB).

```json
// 202 Accepted
{ "lecture_id": "l_123", "status": "processing" }
```

## 2. Get concepts (for the mastery map)

`GET /api/lectures/{lecture_id}/concepts`

```json
{ "lecture_id": "l_123", "status": "ready",
  "concepts": [ /* Concept */ ] }
// status: "processing" | "ready" | "failed" — frontend polls until "ready"
```

## 3. Start a review session

`POST /api/sessions`

```json
// request
{ "lecture_id": "l_123" }
// response
{ "session_id": "s_1", "questions": [ /* Question */ ] }
```

## 4. Submit an answer

`POST /api/answers`

```json
// request
{ "session_id": "s_1", "question_id": "q3", "answer": "B" }
// response
{ "correct": false,
  "concept_id": "c2",
  "feedback": "You mixed up memoization and bottom-up.",
  "citation": { "page": 14, "quote": "Bottom-up fills the table starting from..." },
  "mastery": [ /* Mastery for every concept */ ],
  "next_action": "explain",
  "next_questions": [ /* Question, may be empty */ ] }
// next_action: "next_question" | "explain" | "test_prerequisite" | "done"
```

## 5. Agent trace

`GET /api/sessions/{session_id}/trace?after_step=6` → `{ "events": [ /* Trace event */ ] }`

## 6. Notes and flashcards

`GET /api/sessions/{session_id}/notes`

```json
{ "summary_markdown": "## Dynamic programming ...",
  "weak_concepts": ["c1", "c2"],
  "flashcards": [ { "front": "...", "back": "...", "concept_id": "c2", "page": 14 } ] }
```

`GET /api/sessions/{session_id}/flashcards.csv` → Anki-importable CSV.

## Internal interfaces (backend modules)

| Function | Owner | Input | Output |
| --- | --- | --- | --- |
| `bkt_update(p, correct, params)` | D | prior mastery, answer correct?, BKT params | new mastery 0–1 |
| `label_for(p)` | D | mastery | `mastered` / `confused` / `not_mastered` |
| `next_prerequisite(concept_id, graph, mastery)` | D | failed concept, dependency graph, mastery | concept to test next, or `None` (root found) |
| `search_slides(lecture_id, query, k)` | C | query text | top-k chunks with page numbers |
| `extract_concepts(lecture_id)` | C | lecture | list of Concept |

## Open questions for Nov 2

- Which LLM provider and model? Which agent framework (LangGraph or a hand-written loop)?
- Polling vs streaming (server-sent events) for questions and trace?
- BKT parameters: fixed defaults or per concept?
