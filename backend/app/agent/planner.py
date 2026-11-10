"""The planner: the model reads the learner state and picks the next tool call."""

from __future__ import annotations

from app.agent.llm import UNTRUSTED, Asker, LLMError
from app.agent.policy import Option, Policy, Turn
from app.learner.bkt import label_for, params_for

SYSTEM = f"""TASK: plan
You are the tutoring agent of LectureLoop. A student is reviewing one lecture. Your goal is to find
the ROOT CAUSE of what they do not understand, not just which questions they got wrong, and to keep
teaching until each concept is mastered. {UNTRUSTED}

After every answer you choose the next tool call. Tools:
- trace_root_cause(concept): look up the first prerequisite of that concept the student has not
  shown they know. No such prerequisite means the concept itself is the likely root cause.
- explain(concept): re-explain the concept using the slides, with a page citation.
- generate_quiz(concept): ask the student one new question on that concept. Ends your turn.
- finish: build the notes and flashcards. Ends the session.

How to decide:
- A wrong answer on a concept with an unresolved prerequisite usually means the gap is further
  back: test that prerequisite before re-explaining the concept.
- If the prerequisites are fine, the concept itself is the gap: explain it, then re-test it.
- Once a prerequisite is fixed, go back to the concept that was waiting on it.
- p_mastery of 0.8 or more means mastered. Do not spend questions on mastered concepts.
- When nothing is being diagnosed, cover concepts that are still untested.

Choose exactly one entry of "options" (you cannot do anything else). The entry with
"default": true is what a fixed rule would do; follow it unless the learner state gives you a
reason not to.

Reply with JSON only:
{{"choice": <id of the option>, "reason": "<why, one sentence of at most 25 words>"}}
The reason is shown to the student in the agent trace panel, so write it for them."""


def build_payload(policy: Policy, turn: Turn, options: list[Option], default: Option) -> dict:
    s = policy.session
    prior = params_for()["prior"]
    return {
        "last_answer": {"concept_id": turn.concept_id, "correct": turn.correct},
        "concepts": [
            {
                "id": c.id,
                "name": c.name,
                "prerequisites": c.prerequisites,
                "p_mastery": round(s.p.get(c.id, prior), 2),
                "label": label_for(s.p.get(c.id, prior), tested=c.id in s.p),
                "attempts_left": max(0, policy.max_attempts - s.attempts.get(c.id, 0)),
            }
            for c in policy.lecture.concepts
        ],
        "waiting_on_a_prerequisite_check": list(s.stack),
        "done_this_turn": turn.observations,
        "options": [
            {"id": i, "tool": o.tool, "concept_id": o.concept_id, "default": o == default}
            for i, o in enumerate(options)
        ],
    }


def choose(
    asker: Asker, policy: Policy, turn: Turn, options: list[Option], default: Option
) -> tuple[Option, str] | None:
    """Return the model's (option, reason), or None if it failed or chose something invalid."""
    try:
        data = asker.ask("plan", SYSTEM, build_payload(policy, turn, options, default), retries=0)
    except LLMError:
        return None
    choice = data.get("choice")
    if not isinstance(choice, int) or isinstance(choice, bool) or not 0 <= choice < len(options):
        return None
    reason = data.get("reason")
    reason = " ".join(reason.split())[:240] if isinstance(reason, str) else ""
    return options[choice], reason
