# D learner model: integration notes

## Run deterministic tests

From the repository root, with Python 3.11+:

```sh
python -m pip install pytest
python -m pytest backend/tests/test_bkt.py backend/tests/test_root_cause.py --import-mode=importlib
```

Set `PYTHONPATH=backend` before this command. Alternatively, run from `backend/`:

```sh
python -m pytest tests/test_bkt.py tests/test_root_cause.py
```

Only pytest is required for D's tests. No LLM requests or API keys are needed.

## B integration example

```python
from app.learner.bkt import bkt_update, label_for, params_for
from app.learner.root_cause import next_prerequisite

# Question.type from API contract. Choose params for EACH question.
params = params_for("short_answer", prior=0.30, learn=0.10, slip=0.10)
p = bkt_update(None, True, params)  # None explicitly initializes from prior
record = {"concept_id": "c1", "p_mastery": p, "label": label_for(p)}
graph = [{"id": "c1", "prerequisites": []}, {"id": "c2", "prerequisites": ["c1"]}]
next_id = next_prerequisite("c2", graph, [record])
```

Preserved interfaces: `bkt_update(p, correct, params)`,
`label_for(p, tested=True)`, `next_prerequisite(concept_id, graph, mastery)`.
Additions: `params_for(question_type, **overrides)` and explicit `p=None`
initialization. Existing numeric-p callers need no signature changes.
Missing learn/guess/slip now raises descriptive ValueError, not KeyError.

## Mathematics and timing

For a correct response, posterior = p(1-slip) / [p(1-slip)+(1-p)guess].
For an incorrect response, posterior = p*slip / [p*slip+(1-p)(1-guess)].
Return posterior + (1-posterior)*learn, exactly as in the original branch.
Thus ONE learning transition happens after EACH answer, correct or incorrect.
Do not automatically apply another transition after an explanation. B owns
Agent scheduling; changing the event timing requires a team decision.
There is no forgetting transition. `correct` must be a Python bool.
All probabilities must be finite numbers in [0,1]; bool is rejected.
A zero-likelihood observation raises ValueError: Bayesian conditioning is
undefined, so we do not clip or silently invent a posterior.

MVP assumptions: prior .30, learn .10, slip .10, multiple-choice guess .25,
short-answer guess .05. These are experimental assumptions, NOT fitted or
validated educational parameters. Numeric tests verify implementation,
not accuracy on real learners. Explicit p overrides prior; prior is still
validated if present. Pass `learn=0` only when intentionally choosing to
omit the original learning transition for that call.

## Classification and state

p >= .8: mastered; .5 <= p < .8: confused; p < .5: not_mastered.
Call `label_for(prior, tested=False)` before any answer. `None` is accepted
only for untested classification. B must store answer history/tested status;
probability alone cannot tell whether a concept has been tested.

## Root-cause selection policy

Preserves the prototype: return the FIRST unresolved direct prerequisite
in supplied graph order; do not sort by probability or silently recurse.
Untested, missing mastery or None counts as unresolved regardless of prior.
A tested p < .8 remains unresolved and a hypothesis, not confirmed causality.
After testing, B can explicitly traverse the returned concept's prerequisites.
B must manage visited/tested questions, retry budgets and stop conditions to
avoid repeatedly asking about a low-scoring prerequisite.
`None` means NO unresolved DIRECT prerequisite; it never proves a root cause.

Supported graph inputs:
- original `{id: [direct_prerequisite_ids]}`; include leaves as `id: []`;
- API Concept dictionaries in a list, or `{'concepts': [...]}`;
- C's Pydantic ConceptGraph, or its `model_dump()`.

Supported mastery inputs:
- original `{id: probability}`; None means untested;
- `{id: Mastery_record}` or API list of Mastery records.

Mastery records require a valid label consistent with thresholds. Explicit
untested may contain any valid probability or None. Extra record fields are
ignored. Graph IDs must be nonempty strings. Duplicate IDs/edges, dangling
prerequisites, cycles (even disconnected), unknown target/mastery IDs, invalid
probabilities and inconsistent labels raise ValueError. No input is mutated.
All graph nodes must be explicit: previously an absent graph node could
silently look like a leaf; it is now rejected to avoid false diagnoses.
Validation is iterative O(V+E) per call, with O(V+E) working memory.

## Team decisions still open

1. Draft API's sample labels p=.35 as confused. Current D thresholds classify
   it as not_mastered. We did not change the shared contract; B/A must align
   that example or agree on different thresholds. Inconsistent Mastery records
   are deliberately rejected, including that sample.
2. Confirm original per-answer learning timing versus any future explanation
   event. This change preserves timing and does not implement an Agent loop.
3. B chooses retry limits, evidence needed for a causal claim, multiple-parent
   prioritization changes and how ValueError maps to the API error envelope.
4. All defaults require future calibration; C/B must provide real evaluation
   data before claiming learning-effectiveness or root-cause accuracy.
5. B's implementation was not present in visible main/D/C branches at review;
   only draft interfaces and C's implemented models could be checked.

No B/C source, main, shared API contract, video, survey or pitch was modified.
