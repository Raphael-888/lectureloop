"use client";

// Page 4: the quiz. Left: question, feedback, explanation with a slide citation.
// Right: the tutor chat (ask, or change question type / difficulty) and the collapsed agent trace.

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import QuestionCard from "@/components/QuestionCard";
import StepBar from "@/components/StepBar";
import TracePanel from "@/components/TracePanel";
import TutorChat from "@/components/TutorChat";
import * as api from "@/lib/api";
import type { AnswerResponse, Concept, Mastery, Question, SessionState, TraceEvent } from "@/lib/types";

const LABEL: Record<Mastery["label"], string> = {
  mastered: "mastered",
  confused: "shaky",
  not_mastered: "not yet",
  untested: "untested",
};

export default function QuizPage() {
  const { sessionId } = useParams<{ sessionId: string }>();

  const [state, setState] = useState<SessionState | null>(null);
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [current, setCurrent] = useState<Question | null>(null);
  const [result, setResult] = useState<AnswerResponse | null>(null);
  const [mastery, setMastery] = useState<Record<string, Mastery>>({});
  const [answered, setAnswered] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [showTrace, setShowTrace] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loaded = useRef(false);

  const nameOf = useMemo(() => {
    const names = new Map(concepts.map((c) => [c.id, c.name]));
    return (id: string) => names.get(id) ?? id;
  }, [concepts]);

  // load the session (reload-safe) and the lecture's concept names
  useEffect(() => {
    if (loaded.current) return;
    loaded.current = true;
    (async () => {
      try {
        const s = await api.getSession(sessionId);
        setState(s);
        setCurrent(s.current_question);
        setMastery(Object.fromEntries(s.mastery.map((m) => [m.concept_id, m])));
        setAnswered(s.answered);
        setDone(s.done);
        const c = await api.getConcepts(s.lecture_id);
        setConcepts(c.concepts);
      } catch (e) {
        setError(api.errorMessage(e));
      }
    })();
  }, [sessionId]);

  // poll the agent trace (shown only when the student opens the panel, but kept up to date)
  useEffect(() => {
    if (!state) return;
    let lastStep = 0;
    let busy = false;
    let cancelled = false;
    const tick = async () => {
      if (busy) return;
      busy = true;
      try {
        const r = await api.getTrace(sessionId, lastStep);
        if (!cancelled && r.events.length) {
          lastStep = r.events[r.events.length - 1].step;
          setEvents((prev) => {
            const max = prev.length ? prev[prev.length - 1].step : 0;
            return [...prev, ...r.events.filter((e) => e.step > max)];
          });
        }
      } catch {
        // try again on the next tick
      } finally {
        busy = false;
      }
    };
    tick();
    const timer = setInterval(tick, 1500);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [sessionId, state]);

  async function submit(answer: string) {
    if (!current) return;
    setSubmitting(true);
    setError(null);
    try {
      const r = await api.submitAnswer(sessionId, current.id, answer);
      setResult(r);
      setMastery(Object.fromEntries(r.mastery.map((m) => [m.concept_id, m])));
      setAnswered((n) => n + 1);
    } catch (e) {
      setError(api.errorMessage(e));
    } finally {
      setSubmitting(false);
    }
  }

  function next() {
    if (!result) return;
    const q = result.next_action === "done" ? null : result.next_questions[0] ?? null;
    setResult(null);
    setCurrent(q);
    if (!q) setDone(true);
  }

  async function send(message: string) {
    try {
      await api.chat(sessionId, message);
      setState(await api.getSession(sessionId));
    } catch (e) {
      setError(api.errorMessage(e));
    }
  }

  if (error && !state) return <p className="error narrow">{error}</p>;
  if (!state) {
    return (
      <p className="status narrow">
        <span className="spinner" /> Loading your review…
      </p>
    );
  }

  const scope = state.concept_ids;
  const scopeSet = new Set(scope);
  const masteredCount = scope.filter((id) => mastery[id]?.label === "mastered").length;
  const nextConcept = result?.next_questions[0]?.concept_id;
  const prefs = state.preferences;
  const prefLine = [
    prefs.question_type === "multiple_choice" ? "multiple choice" : prefs.question_type === "short_answer" ? "short answer" : "agent picks the type",
    prefs.difficulty === "same" ? "normal difficulty" : `${prefs.difficulty}`,
  ].join(" · ");

  return (
    <div className="page wide">
      <div className="page-head">
        <div>
          <Link href={`/lecture/${encodeURIComponent(state.lecture_id)}/review`} className="backlink">
            ← Back to concepts
          </Link>
          <h1>Quiz</h1>
        </div>
        <StepBar current={4} />
      </div>

      {/* the selected concepts and how each is doing */}
      <div className="scope-row">
        <span className="muted">Reviewing:</span>
        {scope.map((id) => {
          const m = mastery[id];
          const active = current?.concept_id === id;
          return (
            <span key={id} className={`tag light m-${m?.label ?? "untested"} ${active ? "active" : ""}`}>
              {nameOf(id)} <span className="muted">· {LABEL[m?.label ?? "untested"]}</span>
            </span>
          );
        })}
        <span className="muted grow-right">
          {answered} answered · {masteredCount}/{scope.length} mastered
        </span>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="split">
        <section className="left-pane">
          {current && (
            <div className="question-head">
              {!scopeSet.has(current.concept_id) && (
                <span className="pill warn">Prerequisite check · outside your selection</span>
              )}
              <span className="pill">{current.type === "multiple_choice" ? "Multiple choice" : "Short answer"} · {prefLine}</span>
            </div>
          )}

          {current && (
            <QuestionCard
              key={current.id}
              question={current}
              conceptName={nameOf(current.concept_id)}
              locked={result !== null}
              submitting={submitting}
              onSubmit={submit}
            />
          )}

          {result && (
            <section className={`card feedback ${result.correct ? "ok" : "bad"}`}>
              <h3>{result.correct ? "✓ Correct" : "✗ Not quite"}</h3>
              {result.next_action === "explain" && <div className="eyebrow">Explanation</div>}
              <p>{result.feedback}</p>
              {result.citation && (
                <blockquote className="citation">
                  <strong>Slide p. {result.citation.page}</strong> “{result.citation.quote}”
                </blockquote>
              )}
              <p className="hint">
                {result.next_action === "test_prerequisite" &&
                  nextConcept &&
                  `Tracing the root cause: next we check a prerequisite, ${nameOf(nextConcept)}${scopeSet.has(nextConcept) ? "" : " (not in your selection, but it's where the gap may be)"}.`}
                {result.next_action === "explain" && "Read the explanation, then try a new question on the same idea."}
                {result.next_action === "next_question" &&
                  (nextConcept === result.concept_id
                    ? "One more question to confirm you've got it."
                    : nextConcept
                      ? `Next up: ${nameOf(nextConcept)}.`
                      : "")}
                {result.next_action === "done" && "Every selected concept is covered. Your notes and flashcards are ready."}
              </p>
              <button className="btn primary" onClick={next}>
                {result.next_action === "done" ? "Finish" : "Continue →"}
              </button>
            </section>
          )}

          {done && !result && (
            <section className="card done">
              <h2>🎉 Review complete</h2>
              <p>
                You mastered {masteredCount} of {scope.length} selected concept{scope.length === 1 ? "" : "s"}. Your notes focus
                on the spots you found hardest.
              </p>
              <div className="row center">
                <Link className="btn primary" href={`/session/${encodeURIComponent(sessionId)}/notes`}>
                  See my notes and flashcards →
                </Link>
                <Link className="btn" href={`/lecture/${encodeURIComponent(state.lecture_id)}/review`}>
                  Review other concepts
                </Link>
              </div>
            </section>
          )}

          {!current && !done && !result && (
            <p className="status">
              <span className="spinner" /> Preparing your question…
            </p>
          )}
        </section>

        <aside className="right-pane">
          <TutorChat
            intro="I'll start with multiple choice on the concepts you picked. Ask me anything, or tell me to make it harder, easier, or to switch to short-answer questions."
            messages={state.chat}
            onSend={send}
            suggestions={["Make it harder", "Short answer instead", "Multiple choice please", "Explain that slide again"]}
          />

          <section className="card trace-wrap">
            <button type="button" className="disclosure" onClick={() => setShowTrace((v) => !v)} aria-expanded={showTrace}>
              <span>{showTrace ? "▾" : "▸"} Agent reasoning</span>
              <span className="muted">{events.length} steps</span>
            </button>
            {showTrace && <TracePanel events={events} />}
          </section>
        </aside>
      </div>
    </div>
  );
}
