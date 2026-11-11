"""Guardrails for the agent loop: which tool calls are valid now, and a sensible default.

The model chooses among `options()`; it can never do anything outside that list.
`suggest()` is the deterministic choice used when there is only one option, when
the planner is off, or when the model's answer is unusable.

Invariants this file enforces, whatever the model says:
- a wrong answer is always followed by trace_root_cause before anything else;
- a concept is re-tested only after an explanation, and at most `max_attempts` times;
- the session cannot finish while any concept is neither mastered nor out of attempts,
  so every concept is covered.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.learner.bkt import MASTERY_THRESHOLD
from app.models import Lecture, Session
from app.schemas import Concept

TRACE, EXPLAIN, QUIZ, FINISH = "trace_root_cause", "explain", "generate_quiz", "finish"


@dataclass(frozen=True)
class Option:
    tool: str
    concept_id: str | None = None


@dataclass
class Turn:
    """What has happened since the student's last answer."""

    concept_id: str
    correct: bool
    traced: dict[str, str | None] = field(default_factory=dict)  # concept -> unresolved prerequisite
    explained: str | None = None
    observations: list[str] = field(default_factory=list)  # tool results, fed back to the planner


def pct(p: float) -> str:
    return f"{round(p * 100)}%"


def coverage_order(concepts: list[Concept]) -> list[str]:
    """Most advanced concepts first, so a gap can be traced back through its prerequisites."""
    parents = {c.id: c.prerequisites for c in concepts}
    depth: dict[str, int] = {}

    def visit(cid: str) -> int:
        if cid not in depth:
            depth[cid] = 0  # guard; C's graph check already rejects cycles
            depth[cid] = 1 + max((visit(p) for p in parents.get(cid, []) if p in parents), default=-1)
        return depth[cid]

    first_page = {c.id: min(c.pages) for c in concepts}
    return sorted(parents, key=lambda cid: (-visit(cid), first_page[cid]))


class Policy:
    def __init__(self, lecture: Lecture, session: Session, max_attempts: int):
        self.lecture = lecture
        self.session = session
        self.max_attempts = max_attempts
        self.names = {c.id: c.name for c in lecture.concepts}
        # The review scope: the concepts the student selected (D's review_scope), else the whole
        # lecture. Coverage and finishing look only at the scope; root-cause tracing may still test
        # a prerequisite outside it, because that is where the gap usually is.
        self.targets = list(session.targets) or [c.id for c in lecture.concepts]
        self.order = [cid for cid in coverage_order(lecture.concepts) if cid in self.targets]

    def in_scope(self, cid: str) -> bool:
        return cid in self.targets

    # ---------- concept status ----------

    def mastered(self, cid: str) -> bool:
        return self.session.p.get(cid, 0.0) >= MASTERY_THRESHOLD

    def open(self, cid: str) -> bool:
        """Still worth asking about: not mastered and attempts left."""
        return not self.mastered(cid) and self.session.attempts.get(cid, 0) < self.max_attempts

    def open_concepts(self) -> list[str]:
        """Untested concepts first (coverage), then tested ones that are not mastered yet."""
        todo = [c for c in self.order if self.open(c)]
        return sorted(todo, key=lambda c: c in self.session.p)

    def waiting(self) -> str | None:
        """The concept whose prerequisite is being checked, if it still needs work."""
        s = self.session
        s.stack = [c for c in s.stack if self.open(c)]
        return s.stack[-1] if s.stack else None

    # ---------- valid tool calls ----------

    def options(self, turn: Turn) -> list[Option]:
        x, s = turn.concept_id, self.session
        if not turn.correct and self.open(x) and x not in turn.traced:
            return [Option(TRACE, x)]

        top = self.waiting()
        opts: list[Option] = []
        quiz: list[str] = []

        if not turn.correct and self.open(x):
            prereq = turn.traced.get(x)
            if prereq and self.open(prereq):
                quiz.append(prereq)
            if turn.explained == x:
                quiz.append(x)
            elif turn.explained is None:
                opts.append(Option(EXPLAIN, x))
        else:
            if not turn.correct and turn.explained is None:
                opts.append(Option(EXPLAIN, x))  # out of attempts: still explain before moving on
            if self.open(x):
                quiz.append(x)  # correct, but not yet at the mastery threshold
            if top:
                if turn.correct and not self.open(x) and top not in turn.traced:
                    opts.append(Option(TRACE, top))
                prereq = turn.traced.get(top)
                if prereq and self.open(prereq):
                    quiz.append(prereq)
                if turn.correct and turn.explained is None and top in s.wrong and not self.open(x):
                    opts.append(Option(EXPLAIN, top))
                quiz.append(top)
            if not quiz:
                quiz = self.open_concepts()

        opts += [Option(QUIZ, c) for c in dict.fromkeys(quiz)]
        if not self.open_concepts():
            opts.append(Option(FINISH))
        return opts

    # ---------- default choice ----------

    def suggest(self, turn: Turn, options: list[Option]) -> tuple[Option, str]:
        x, s, name = turn.concept_id, self.session, self.names
        top = self.waiting()

        def has(tool: str, cid: str | None = None) -> bool:
            return Option(tool, cid) in options

        if has(TRACE, x):
            return Option(TRACE, x), f"{name[x]} answered wrong; check whether a prerequisite is the real gap"

        if not turn.correct:
            prereq = turn.traced.get(x)
            if prereq and has(QUIZ, prereq):
                return Option(QUIZ, prereq), f"{name[x]} below threshold; testing prerequisite {name[prereq]}"
            if has(EXPLAIN, x):
                return Option(
                    EXPLAIN, x
                ), f"{name[x]} is the likely root cause; re-explain it with slide evidence"
            if has(QUIZ, x):
                return Option(QUIZ, x), f"Re-test {name[x]} with a new question after the explanation"
        elif has(QUIZ, x):
            reason = (
                f"{name[x]} at {pct(s.p[x])}, below the {pct(MASTERY_THRESHOLD)} mastery threshold; confirm"
            )
            return Option(QUIZ, x), reason
        elif top:
            if x in s.wrong and has(QUIZ, top):
                return Option(QUIZ, top), f"Prerequisite {name[x]} fixed; returning to {name[top]}"
            if has(TRACE, top):
                return Option(
                    TRACE, top
                ), f"{name[x]} is not the gap; check the other prerequisites of {name[top]}"
            prereq = turn.traced.get(top)
            if prereq and has(QUIZ, prereq):
                return Option(QUIZ, prereq), f"Testing the next prerequisite of {name[top]}: {name[prereq]}"
            if has(EXPLAIN, top):
                return Option(
                    EXPLAIN, top
                ), f"Prerequisites of {name[top]} check out; the gap is {name[top]} itself"

        if top and has(QUIZ, top):
            if turn.explained == top:
                return Option(QUIZ, top), f"Re-test {name[top]} with a new question after the explanation"
            return Option(QUIZ, top), f"Returning to {name[top]}, which was waiting on this check"
        for cid in self.open_concepts():
            if has(QUIZ, cid):
                if cid not in s.p:
                    left = sum(1 for c in self.order if c not in s.p)
                    return Option(QUIZ, cid), f"Coverage: {name[cid]} not tested yet ({left} concepts left)"
                return Option(QUIZ, cid), f"{name[cid]} still at {pct(s.p[cid])}; try again"
        if has(FINISH):
            return Option(
                FINISH
            ), "Every concept is mastered or out of attempts; build notes on the weak spots"
        return options[0], "Only valid next step"
