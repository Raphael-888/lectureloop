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
