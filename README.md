# LectureLoop

> An AI agent that finds the root cause of what you don't understand — not just which questions you got wrong.

Team **deep sleep** · [Cognizant BrAInstorm Challenge 2026](https://shiftkeylabs.ca/event/cognizant-brainstorm-challenge-2026/) · Track: Education · Theme: Agentic AI for Good

## What it does

A student uploads the slides from one lecture. The agent:

1. Extracts every key concept and the prerequisite links between them, each tied to its slide pages.
2. Generates a quiz that covers every concept.
3. Grades answers and builds a mastery map (Bayesian Knowledge Tracing).
4. For each gap, traces the root cause through prerequisite concepts, re-explains with slide citations, and re-tests until mastered.
5. Produces personalized notes and flashcards (exportable to Anki) focused on weak spots.

## Repository layout

```
frontend/   Next.js web app (upload, quiz, mastery map, agent trace, notes)
backend/    FastAPI + agent, tools, BKT model, PDF retrieval
docs/       API contract, design decisions, evaluation results
```

## Team

| Role | Owner | Responsibility |
| --- | --- | --- |
| A · Frontend | TBD | All pages, mastery map, agent trace panel |
| B · Agent & backend (tech lead) | TBD | FastAPI, agent loop, quiz, grading, root-cause tracing |
| C · Slides, data & output | TBD | PDF parsing, retrieval, concept extraction, database, notes & flashcards, security, deploy |
| D · Learning model, evaluation & pitch | TBD | BKT model, root-cause rules, evaluation, survey, video, pitch |

## Key dates

| Date | Milestone |
| --- | --- |
| Nov 1, 11:59 PM | Idea submission |
| Nov 2 | Kickoff: freeze API contract, pick tech stack |
| Nov 13 | Full-team integration day |
| Nov 15, 11:59 PM | MVP + 3-minute video due |
| Nov 21 | Finalists announced |
| Nov 28, 1–3 PM | Final pitch in Halifax (5 min + demo) |

## Getting started

Setup instructions will be added once the stack is set up (see `frontend/README.md` and `backend/README.md`).

## Working together

- Work on your own branch (`a/…`, `b/…`, `c/…`, `d/…`), open a Pull Request, and get one teammate to review before merging into `main`.
- Never commit API keys. Put secrets in `backend/.env` (already ignored by git); share `backend/.env.example` instead.
- If you need to change the API contract, update `docs/api-contract.md` in the same PR and tell the team.
- Daily async update in the group chat: what I did, what I'm stuck on.
