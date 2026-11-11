"""The agent loop: after every answer the agent calls tools until it has a next question.

Per answer:
  grade_answer -> update_mastery (D's BKT)                      always
  then repeat: planner picks one valid tool call (policy.py)    model decides
      trace_root_cause | explain (+ search_slides) | generate_quiz | finish
  until generate_quiz or finish ends the turn.

Every tool call is appended to the session trace with the reason it was made.
"""

from __future__ import annotations

import time

from app.agent import planner
from app.agent.explain import explain
from app.agent.grading import grade
from app.agent.llm import LLM, Asker, LLMError, get_llm
from app.agent.policy import EXPLAIN, FINISH, QUIZ, TRACE, Policy, Turn, pct
from app.agent.quiz import pick
from app.agent.search import search_pages
from app.config import Settings
from app.errors import ApiError
from app.learner.bkt import bkt_update, label_for, params_for
from app.learner.root_cause import next_prerequisite
from app.models import AnswerResponse, Lecture, Mastery, Question, QuestionItem, RootCause, Session
from app.store import Store

KIND = {"multiple_choice": "multiple-choice", "short_answer": "short-answer"}


class _NoLLM:
    """Stands in when no model is configured: every call fails, so tools use their fallbacks."""

    def complete_json(self, system: str, user: str) -> str:
        raise LLMError("no LLM configured")


def mastery_list(lecture: Lecture, session: Session) -> list[Mastery]:
    prior = params_for()["prior"]
    out = []
    for c in lecture.concepts:
        tested = c.id in session.p
        p = session.p.get(c.id, prior)
        out.append(Mastery(concept_id=c.id, p_mastery=round(p, 3), label=label_for(p, tested=tested)))
    return out


class Agent:
    def __init__(
        self, store: Store, lecture: Lecture, session: Session, settings: Settings, llm: LLM | None = None
    ):
        self.store = store
        self.lecture = lecture
        self.session = session
        self.settings = settings
        if llm is None:
            try:
                llm = get_llm()
            except LLMError:
                llm = _NoLLM()
        self.use_planner = settings.planner == "llm" and not isinstance(llm, _NoLLM)
        self.asker = Asker(llm, store, session.id)
        self.policy = Policy(lecture, session, settings.max_attempts)
        self.names = self.policy.names

    # ---------- session start ----------

    def start(self) -> list[Question]:
        s, lec = self.session, self.lecture
        links = sum(len(c.prerequisites) for c in lec.concepts)
        s.add_trace(
            "extract_concepts",
            f"Read {lec.title or lec.filename} before quizzing",
            f"Found {len(lec.concepts)} concepts and {links} prerequisite links on {len(lec.pages)} pages",
        )
        if s.targets:
            chosen = ", ".join(self.names[c] for c in s.targets)
            s.add_trace(
                "review_scope",
                "The student chose what to review; quiz only those concepts",
                f"Scope: {chosen} ({len(s.targets)} of {len(lec.concepts)} concepts)",
            )
        if s.scope_summary:
            n = len(self.policy.targets)
            s.add_trace(
                "summarize",
                "Summarise what is being reviewed before the first question",
                f"Summary of {n} concept{'s' if n != 1 else ''} written from the slides",
            )
        first = self.policy.order[0]
        item = self._issue(
            first, "Coverage pass: start with the most advanced concept so gaps can be traced back"
        )
        return [item.public()]

    # ---------- one answer ----------

    def answer(self, question_id: str, answer: str) -> AnswerResponse:
        s = self.session
        if question_id in s.responses:  # client retry: same result, no double BKT update
            return AnswerResponse.model_validate(s.responses[question_id])
        item = s.issued.get(question_id)
        if item is None:
            raise ApiError(404, "question_not_found", f"No question with id {question_id} in this session")
        if question_id != s.current_question:
            raise ApiError(409, "question_not_active", "This is not the question currently being asked")

        started = time.perf_counter()
        cid = item.concept_id
        name = self.names[cid]

        correct, graded_feedback, method = grade(self.asker, item, answer)
        s.answers[question_id] = answer
        s.current_question = None
        shown = " ".join(answer.split())[:40] or "blank"
        how = {"key": "", "llm": " (model graded against the rubric)", "keywords": " (keyword fallback)"}[
            method
        ]
        s.add_trace(
            "grade_answer",
            f'Grade the answer to "{name}"',
            ("Correct" if correct else f"Incorrect (answered: {shown})") + how,
        )

        params = params_for(item.type)
        before = s.p.get(cid)
        after = bkt_update(before, correct, params)
        start = params["prior"] if before is None else before
        s.p[cid] = after
        s.attempts[cid] = s.attempts.get(cid, 0) + 1
        if not correct:
            s.last_wrong[cid] = question_id
            if cid not in s.wrong:
                s.wrong.append(cid)
        s.add_trace(
            "update_mastery",
            "Update BKT mastery for the tested concept",
            f"{name}: {pct(start)} → {pct(after)} ({label_for(after)})",
        )

        turn = Turn(concept_id=cid, correct=correct)
        turn.observations.append(
            f"grade_answer: {'correct' if correct else 'incorrect'} on {cid}; p_mastery is now {after:.2f}"
        )
        next_item, is_prerequisite, finished = self._act(turn)

        if finished:
            action = "done"
        elif turn.explained:
            action = "explain"
        elif is_prerequisite:
            action = "test_prerequisite"
        else:
            action = "next_question"

        explanation = s.explanations.get(turn.explained) if turn.explained else None
        response = AnswerResponse(
            correct=correct,
            concept_id=cid,
            feedback=self._feedback(item, correct, graded_feedback, turn, action),
            citation=explanation.citation if explanation else None,
            mastery=mastery_list(self.lecture, s),
            next_action=action,
            next_questions=[next_item.public()] if next_item else [],
        )
        s.responses[question_id] = response.model_dump()
        self.store.log_answer(
            session_id=s.id,
            lecture_id=s.lecture_id,
            question_id=question_id,
            concept_id=cid,
            question_type=item.type,
            correct=int(correct),
            p_before=before,
            p_after=after,
            next_action=action,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        return response

    def _act(self, turn: Turn) -> tuple[QuestionItem | None, bool, bool]:
        """Run tool calls until the turn ends. Returns (next question, is prerequisite test, finished)."""
        max_steps = self.settings.max_agent_steps
        for step in range(max_steps * 2):
            options = self.policy.options(turn)
            choice, reason = self.policy.suggest(turn, options)
            if self.use_planner and len(options) > 1 and step < max_steps:
                picked = planner.choose(self.asker, self.policy, turn, options, choice)
                if picked is not None:
                    reason = picked[1] or (reason if picked[0] == choice else "Chosen by the agent")
                    choice = picked[0]

            if choice.tool == TRACE:
                self._trace_root_cause(turn, choice.concept_id, reason)
            elif choice.tool == EXPLAIN:
                self._explain(turn, choice.concept_id, reason)
            elif choice.tool == QUIZ:
                target = choice.concept_id
                is_prerequisite = any(pre == target for c, pre in turn.traced.items() if c != target)
                return self._issue(target, reason, turn), is_prerequisite, False
            elif choice.tool == FINISH:
                self._finish(reason)
                return None, False, True
        raise RuntimeError("agent loop did not reach a terminal tool")  # policy bug, never the model

    # ---------- tools ----------

    def _trace_root_cause(self, turn: Turn, cid: str, reason: str) -> None:
        s = self.session
        closed = {c.id for c in self.lecture.concepts if not self.policy.open(c.id)}
        graph = {c.id: [p for p in c.prerequisites if p not in closed] for c in self.lecture.concepts}
        mastery = {c.id: s.p.get(c.id) for c in self.lecture.concepts}  # None = untested
        try:
            prereq = next_prerequisite(cid, graph, mastery)  # D's rule: one level at a time
        except ValueError:
            prereq = None
        turn.traced[cid] = prereq

        name = self.names[cid]
        parents = self.lecture.concept(cid).prerequisites
        # prerequisites the student never got right, even after the agent's attempts ran out
        stuck = [p for p in parents if p in closed and not self.policy.mastered(p)]
        if prereq:
            state = pct(s.p[prereq]) if prereq in s.p else "untested"
            outside = "" if self.policy.in_scope(prereq) else ", outside the selection"
            summary = f"Unresolved prerequisite of {name}: {self.names[prereq]} ({state}{outside})"
            turn.observations.append(f"trace_root_cause({cid}): unresolved prerequisite {prereq} ({state})")
        elif stuck:
            # the gap is still further back, so this concept is a symptom, not a root cause
            below = ", ".join(self.names[p] for p in stuck)
            summary = f"{name} still depends on {below}, which is not mastered yet: the root cause is there"
            turn.observations.append(f"trace_root_cause({cid}): prerequisite {stuck[0]} was never mastered")
        else:
            checked = (
                f"All prerequisites of {name} check out" if parents else f"{name} has no prerequisites here"
            )
            summary = f"{checked}. Likely root cause: {name}"
            turn.observations.append(
                f"trace_root_cause({cid}): no unresolved prerequisite; {cid} is the likely root cause"
            )
            symptom = s.stack[0] if s.stack else cid
            if not any(r.root == cid for r in s.root_causes):
                s.root_causes.append(RootCause(symptom=symptom, root=cid, step=len(s.trace) + 1))
        s.add_trace("trace_root_cause", reason, summary)

    def _explain(self, turn: Turn, cid: str, reason: str) -> None:
        s = self.session
        concept = self.lecture.concept(cid)
        question_id = s.last_wrong.get(cid, "")
        chunks = search_pages(
            self.lecture.pages, f"{concept.name} {concept.summary}", k=3, prefer=concept.pages
        )
        pages = ", ".join(str(c["page"]) for c in chunks)
        s.add_trace(
            "search_slides",
            f"Find slide evidence to re-explain {concept.name}",
            f"Top pages: {pages}" if chunks else "No slide text matched",
        )
        result = explain(
            self.asker, concept, s.issued.get(question_id), s.answers.get(question_id, ""), chunks
        )
        s.explanations[cid] = result
        turn.explained = cid
        cited = f", citing slide p. {result.citation.page}" if result.citation else ""
        turn.observations.append(f"explain({cid}): explanation written{cited}")
        s.add_trace("explain", reason, f"Explained {concept.name}{cited}")

    def _issue(self, cid: str, reason: str, turn: Turn | None = None) -> QuestionItem:
        s = self.session
        item = pick(
            self.store,
            self.lecture,
            s,
            cid,
            self.asker,
            self.settings.enable_short_answer,
            preferences=s.preferences,
        )
        s.issued[item.id] = item
        s.current_question = item.id
        if cid in s.stack:  # returning to a waiting concept: drop it and anything above it
            s.stack = s.stack[: s.stack.index(cid)]
        if turn is not None:
            for waiting, prereq in turn.traced.items():
                if prereq == cid and waiting not in s.stack and self.policy.open(waiting):
                    s.stack.append(waiting)
        s.add_trace("generate_quiz", reason, f"1 {KIND[item.type]} question on {self.names[cid]}")
        return item

    def _finish(self, reason: str) -> None:
        s = self.session
        s.done = True
        s.stack = []
        reviewed = [c.id for c in self.lecture.concepts if self.policy.in_scope(c.id) or c.id in s.p]
        weak = [cid for cid in reviewed if cid in s.wrong or not self.policy.mastered(cid)]
        s.add_trace("export_flashcards", reason, f"Notes and flashcards ready ({len(weak)} weak concepts)")

    # ---------- feedback text ----------

    def _feedback(self, item: QuestionItem, correct: bool, graded: str, turn: Turn, action: str) -> str:
        name = self.names[item.concept_id]
        explanation = self.session.explanations.get(turn.explained) if turn.explained else None
        if correct:
            text = graded or f"Correct. {item.reference}".strip()
            if explanation and turn.explained != item.concept_id:
                gap = self.names[turn.explained]
                text += f" So the prerequisites are fine: the gap is {gap} itself. {explanation.text}"
            return text
        if explanation:
            return explanation.text
        if action == "test_prerequisite":
            return (
                f"Not quite. Before re-explaining {name}, let's check whether a prerequisite is the real gap."
            )
        return f"Not quite. {graded}".strip()
