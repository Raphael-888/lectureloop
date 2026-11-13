"use client";

// Page 4: the quiz. Back link top left, settings top right, a star on every question, Next,
// the tutor as a floating box, and End (back to the main page). Agent trace stays collapsed.

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import FloatingChat from "@/components/FloatingChat";
import QuestionCard from "@/components/QuestionCard";
import QuizSettings from "@/components/QuizSettings";
import TracePanel from "@/components/TracePanel";
import * as api from "@/lib/api";
import type { AnswerResponse, Concept, Mastery, PreferencesUpdate, Question, SessionState, TraceEvent } from "@/lib/types";

const LABEL: Record<Mastery["label"], string> = {
  mastered: "mastered",
  confused: "getting there",
  not_mastered: "needs work",
  untested: "not yet",
};

export default function QuizPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const router = useRouter();

  const [state, setState] = useState<SessionState | null>(null);
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [current, setCurrent] = useState<Question | null>(null);
  const [result, setResult] = useState<AnswerResponse | null>(null);
  const [mastery, setMastery] = useState<Record<string, Mastery>>({});
  const [answered, setAnswered] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [starred, setStarred] = useState<Set<string>>(new Set());
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [showTrace, setShowTrace] = useState(false);
  const [ending, setEnding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loaded = useRef(false);

  const nameOf = useMemo(() => {
    const names = new Map(concepts.map((c) => [c.id, c.name]));
    return (id: string) => names.get(id) ?? id;
  }, [concepts]);

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
        const [c, b] = await Promise.all([api.getConcepts(s.lecture_id), api.getBookmarks(s.lecture_id)]);
        setConcepts(c.concepts);
        setStarred(new Set(b.items.map((i) => i.question.id)));
      } catch (e) {
        setError(api.errorMessage(e));
      }
    })();
  }, [sessionId]);

  // keep the (collapsed) agent trace up to date
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
        // next tick
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

  async function star(questionId: string) {
    if (!state) return;
    try {
      const r = await api.toggleBookmark(state.lecture_id, questionId, sessionId);
      setStarred(new Set(r.items.map((i) => i.question.id)));
    } catch (e) {
      setError(api.errorMessage(e));
    }
  }

  async function send(message: string) {
    try {
      await api.chat(sessionId, message);
      setState(await api.getSession(sessionId));
    } catch (e) {
      setError(api.errorMessage(e));
    }
  }

  async function changePrefs(update: PreferencesUpdate) {
    try {
      setState(await api.setPreferences(sessionId, update));
    } catch (e) {
      setError(api.errorMessage(e));
    }
  }

  async function end() {
    if (!state) return;
    setEnding(true);
    try {
      await api.finishSession(sessionId);
      router.push(`/lecture/${encodeURIComponent(state.lecture_id)}`);
    } catch (e) {
      setError(api.errorMessage(e));
      setEnding(false);
    }
  }

  if (error && !state) return <p className="error narrow">{error}</p>;
  if (!state) {
    return (
      <p className="status narrow">
        <span className="spinner" /> Loading your quiz…
      </p>
    );
  }

  const scope = state.concept_ids;
  const scopeSet = new Set(scope);
  const masteredCount = scope.filter((id) => mastery[id]?.label === "mastered").length;
  const nextConcept = result?.next_questions[0]?.concept_id;
  const lectureHref = `/lecture/${encodeURIComponent(state.lecture_id)}`;

  return (
    <div className="page quiz-page">
      <div className="page-head">
        <div>
          <Link href={`/session/${encodeURIComponent(sessionId)}`} className="backlink">
            ← Back to the review
          </Link>
          <h1>{scope.map(nameOf).join(" & ")}</h1>
        </div>
        <div className="row" style={{ marginTop: 0, alignItems: "center" }}>
          <QuizSettings prefs={state.preferences} onChange={changePrefs} />
          {!done && (
            <button type="button" className="btn" disabled={ending} onClick={end}>
              {ending ? "Ending…" : "End"}
            </button>
          )}
        </div>
      </div>

      <div className="scope-row">
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

      {current && (
        <div className="question-head">
          {!scopeSet.has(current.concept_id) && <span className="pill warn">Prerequisite check · outside your selection</span>}
          <span className="pill">{current.type === "multiple_choice" ? "Multiple choice" : "Short answer"}</span>
          <button
            type="button"
            className={`star ${starred.has(current.id) ? "on" : ""}`}
            aria-pressed={starred.has(current.id)}
            aria-label={starred.has(current.id) ? "Remove from saved questions" : "Save this question"}
            title="Save this question to practise again"
            onClick={() => star(current.id)}
          >
            {starred.has(current.id) ? "★ Saved" : "☆ Save"}
          </button>
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
              (nextConcept === result.concept_id ? "One more question to confirm you've got it." : nextConcept ? `Next up: ${nameOf(nextConcept)}.` : "")}
            {result.next_action === "done" && "Every selected concept is covered."}
          </p>
          <div className="row" style={{ marginTop: 8 }}>
            {!result.correct && current && !starred.has(current.id) && (
              <button type="button" className="btn" onClick={() => star(current.id)}>
                ☆ Save to practise again
              </button>
            )}
            <button className="btn primary" onClick={next}>
              {result.next_action === "done" ? "Finish" : "Next →"}
            </button>
          </div>
        </section>
      )}

      {done && !result && (
        <section className="card done">
          <h2>🎉 Done</h2>
          <p>
            You mastered {masteredCount} of {scope.length} selected concept{scope.length === 1 ? "" : "s"}. The concept map is
            updated with what you know now.
          </p>
          <div className="row center">
            <Link className="btn primary" href={lectureHref}>
              Back to all concepts →
            </Link>
            <Link className="btn" href={`/session/${encodeURIComponent(sessionId)}/notes`}>
              Notes &amp; flashcards
            </Link>
          </div>
        </section>
      )}

      {!current && !done && !result && (
        <p className="status">
          <span className="spinner" /> Preparing your question…
        </p>
      )}

      <section className="card trace-wrap">
        <button type="button" className="disclosure" onClick={() => setShowTrace((v) => !v)} aria-expanded={showTrace}>
          <span>{showTrace ? "▾" : "▸"} Agent reasoning</span>
          <span className="muted">{events.length} steps</span>
        </button>
        {showTrace && <TracePanel events={events} />}
      </section>

      <FloatingChat messages={state.chat} onSend={send} />
    </div>
  );
}
