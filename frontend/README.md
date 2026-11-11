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
start the FastAPI server on `BACKEND_URL`, and restart `npm run dev`.

## Pages

| Route | Page |
| --- | --- |
| `/` | Upload slides, wait for processing, preview the concept list |
| `/lecture/[lectureId]/study` | Quiz + live mastery map + agent trace panel |
| `/session/[sessionId]/notes` | Notes, flashcards, Anki CSV export |

## Code layout

```
app/            pages (Next.js App Router)
components/     QuestionCard, MasteryMap (React Flow), TracePanel, FlashcardDeck
lib/types.ts    types copied from docs/api-contract.md
lib/api.ts      the ONLY file that calls the backend; switches between mock and real
lib/mock/       demo lecture (C's CSCI 3151 M04 concept graph) and a mock agent loop
```

`/api/*` requests are forwarded to `BACKEND_URL` by `next.config.mjs`, so the backend
does not need CORS for local development.
