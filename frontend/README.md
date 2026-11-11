# Frontend (Next.js)

Owner: A.

## Run it

Requires Node.js 20+.

```bash
cd frontend
npm install        # first time only
npm run dev        # open http://localhost:3000
```

By default the app runs on **mock data** (no backend needed): click **Try the demo lecture**.
To use the real backend, copy `.env.example` to `.env.local`, set `NEXT_PUBLIC_USE_MOCK=false`,
start the FastAPI server on `BACKEND_URL` (see `backend/README.md`; `LLM_PROVIDER=offline` works
without a key), and restart `npm run dev`.

## Flow (Nov 10 product decision: review what you pick)

| Route | Page |
| --- | --- |
| `/` | 1 · Upload slides, wait for processing |
| `/lecture/[lectureId]` | 2 · Overview: summary + the concepts as a tree in lecture order |
| `/lecture/[lectureId]/review` | 3 · Pick concepts: mind map / original PDF on the left, drag-and-drop review box on the right; after Submit: AI summary + tutor chat + Next |
| `/session/[sessionId]` | 4 · Quiz on the selected concepts, tutor chat (ask, or change question type / difficulty), collapsed "Agent reasoning" panel |
| `/session/[sessionId]/notes` | Notes, flashcards, Anki CSV export |

## Code layout

```
app/            pages (Next.js App Router)
components/     ConceptBlocks (tree + drag chips), ReviewBox, PdfPages, TutorChat, QuestionCard,
                TracePanel, FlashcardDeck, StepBar, Markdown
lib/types.ts    types copied from docs/api-contract.md
lib/api.ts      the ONLY file that calls the backend; switches between mock and real
lib/groups.ts   groups a flat concept list into topic blocks for the tree views
lib/useLecture  loads a lecture's concepts (polls while processing)
lib/mock/       demo lecture (C's CSCI 3151 M04 concept graph) and a mock agent loop
```

`/api/*` requests are forwarded to `BACKEND_URL` by `next.config.mjs`, so the backend
does not need CORS for local development.
