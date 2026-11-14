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

## Flow (Nov 12 meeting + sketch)

| Route | Page |
| --- | --- |
| `/` | 1 · Upload slides, wait for processing |
| `/lecture/[lectureId]` | 2 · **Main page**: the concepts "explode" over the page, coloured by mastery across all sessions; click to select, confirm → session. ★ button opens the saved questions (mistake book) |
| `/session/[sessionId]` | 3 · **Review**: "A & B" title, AI summary, tutor chat, PDF button (split view with the slides for these concepts, draggable divider), Start quiz |
| `/session/[sessionId]/quiz` | 4 · **Quiz**: back link, ☆ save on each question, ⚙ question type / difficulty picker, floating tutor, End → main page. "Agent reasoning" collapsed at the bottom |
| `/session/[sessionId]/notes` | Notes, flashcards, Anki CSV export |

## Code layout

```
app/            pages (Next.js App Router)
components/     ConceptCloud (exploded boxes), BookmarksDrawer, SplitPane, PdfPages, TutorChat,
                FloatingChat, QuizSettings, QuestionCard, TracePanel, FlashcardDeck, StepBar, Markdown
lib/types.ts    types copied from docs/api-contract.md
lib/api.ts      the ONLY file that calls the backend; switches between mock and real
lib/useLecture  loads a lecture's concepts (polls while processing)
lib/mock/       demo lecture (our own, see docs/demo-lecture/) and a mock agent loop
```

`/api/*` requests are forwarded to `BACKEND_URL` by `next.config.mjs`, so the backend
does not need CORS for local development.
