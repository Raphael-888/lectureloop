# Selected concept review integration

This additive D module supports the November product discussion: students select
one or more concepts and may mark concepts for focused practice. Existing BKT
functions, thresholds, root-cause rules and transition timing are unchanged.
All helpers are pure and return JSON-serializable values. They do not create
accounts, persist sessions, generate questions or change the public API contract.

## Calls for B

```python
from app.learner.review import (
    review_scope, review_progress, campfire_candidates, prerequisite_check,
)

targets = review_scope(["merge_sort", "quicksort"], graph)
progress = review_progress(targets, graph, mastery)
practice = campfire_candidates(targets, graph, mastery, marked_ids=["merge_sort"])
check = prerequisite_check("quicksort", targets, graph, mastery)
```

Use the full C concept graph with stable IDs. Selection is an ordered subset,
not a new merged concept or a pruned dependency graph. Duplicate selections are
deduplicated. Empty selection stays empty; the API should ask the user to select
a concept before starting. Missing mastery remains untested. API Concept and
Mastery records, adjacency maps and C's ConceptGraph are accepted as before.

`prerequisite_check` returns either None or a candidate with `outside_scope`.
An outside-scope candidate is a diagnostic suggestion, not authorization to
expand the quiz. B must decide the UI/Agent policy for offering that check.
For deeper traversal, B can use the unchanged `next_prerequisite` function.
Neither helper establishes a proven root cause.

`campfire_candidates` combines tested weakness with explicit self-report only
within the supplied selection. Reasons are `tested_weak` and `self_reported`.
It includes a marked mastered concept without lowering its probability. It
does not mark every untested concept weak or automatically clear user marks.
C/B should store marks separately from probabilities and answer history.

`review_progress` counts only unique selected concepts. `mastered_fraction`
is mastered / selected, with None for an empty selection. It is not a monetary
refund, a calibrated learning gain or a signal that the session must finish.
Attempts exhausted and mastery attained remain different outcomes.

## Required team wiring and decisions

- B: add optional selected concept IDs to the session request, validate them,
  and scope quiz coverage, planner choices and termination to those targets.
  The currently inspected SessionRequest only accepts lecture_id. Adding this
  helper alone does not enable selection in the running Agent.
- B/A: agree whether prerequisite checks may temporarily leave the selection.
  The helper exposes this explicitly and does not decide it silently.
- C/B: store campfire marks and per-concept evidence in the session, even with
  no account system. Decide how users remove marks and whether review clears them.
- B: continue to grade evidence per concept. Selecting multiple concepts means
  a question bank spanning them; do not apply one aggregate correct/incorrect
  result to every selected concept. Joint questions need separately graded
  evidence or an agreed attribution model before BKT updates.
- B: existing multiple_choice and short_answer defaults remain experimental.
  Proof and calculation questions need an agreed grading rubric and explicit
  parameters; do not invent new defaults or silently map unknown types.
  Existing bkt_update accepts explicit guess/learn/slip/prior parameters.
- A: drag-and-drop, PDF switching, chatbot, hidden trace and tuition visuals
  are UI/Agent work. Hiding trace does not require deleting evaluation logs.
- D/B: viewing a summary, chatting, marking a concept or selecting a topic is
  not a graded answer and must not trigger bkt_update. The existing one learning
  transition after a graded answer remains unchanged.

## Evaluation

Run the existing D tests plus test_review.py. Added cases cover selection order,
duplicates, empty scope, out-of-scope prerequisites, untested high priors,
campfire self-report versus evidence, API record formats, no input mutation,
cycles, missing IDs and invalid probabilities. These are model/helper tests;
new selected-scope UI/Agent end-to-end tests require B/A wiring above.
