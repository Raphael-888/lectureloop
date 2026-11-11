"use client";

// Page 2–4: quiz + live mastery map + agent trace, on one screen for the demo.

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import MasteryMap from "@/components/MasteryMap";
import QuestionCard from "@/components/QuestionCard";
import TracePanel from "@/components/TracePanel";
import * as api from "@/lib/api";
import type { AnswerResponse, Concept, Mastery, Question, TraceEvent } from "@/lib/types";

export default function StudyPage() {
  const { lectureId } = useParams<{ lectureId: string }>();

  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [current, setCurrent] = useState<Question | null>(null);
  const [queue, setQueue] = useState<Question[]>([]);
  const [result, setResult] = useState<AnswerResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [mastery, setMastery] = useState<Record<string, Mastery>>({});
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [answered, setAnswered] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  const nameOf = useMemo(() => {
    const names = new Map(concepts.map((c) => [c.id, c.name]));
    return (id: string) => names.get(id) ?? id;
  }, [concepts]);

  // load concepts and start a session (once, even in React dev double-render)
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    (async () => {
      try {
        const c = await api.getConcepts(lectureId);
        if (c.status !== "ready") throw new Error("This lecture is still processing. Go back and wait a moment.");
        setConcepts(c.concepts);
        const s = await api.startSession(lectureId);
        setSessionId(s.session_id);
        setCurrent(s.questions[0] ?? null);
        setQueue(s.questions.slice(1));
      } catch (e) {
        setError(api.errorMessage(e));
      }
    })();
  }, [lectureId]);

  // poll the agent trace for new steps
  useEffect(() => {
    if (!sessionId) return;
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
        // ignore and try again on the next tick
      } finally {
        busy = false;
      }
    };
    tick();
    const timer = setInterval(tick, 1200);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [sessionId]);

  async function submit(answer: string) {
    if (!sessionId || !current) return;
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
    // questions chosen by the agent go first, then whatever was already queued
    const upcoming = result.next_action === "done" ? [] : [...result.next_questions, ...queue];
    setResult(null);
    if (upcoming.length === 0) {
      setDone(true);
      setCurrent(null);
      setQueue([]);
      return;
    }
    setCurrent(upcoming[0]);
    setQueue(upcoming.slice(1));
  }

  const masteredCount = Object.values(mastery).filter((m) => m.label === "mastered").length;
  const nextConcept = result?.next_questions[0]?.concept_id;

  return (
    <div className="study">
      <div className="study-left">
        <div className="progress">
          <span>
            {answered} answered · {masteredCount}/{concepts.length || "–"} mastered
          </span>
          <div className="bar">
            <div style={{ width: `${concepts.length ? (masteredCount / concepts.length) * 100 : 0}%` }} />
          </div>
        </div>

        {error && <p className="error">{error}</p>}

        {!error && !current && !done && (
          <p className="status">
            <span className="spinner" /> Preparing your quiz…
          </p>
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
                `Tracing the root cause: next we check a prerequisite, ${nameOf(nextConcept)}.`}
              {result.next_action === "explain" && "Read the explanation, then try a new question on the same idea."}
              {result.next_action === "next_question" &&
                (nextConcept === result.concept_id
                  ? "One more question to confirm you've got it."
                  : nextConcept
                    ? `Next up: ${nameOf(nextConcept)}.`
                    : "")}
              {result.next_action === "done" && "Every concept is covered. Your notes and flashcards are ready."}
            </p>
            <button className="btn primary" onClick={next}>
              {result.next_action === "done" ? "Finish" : "Continue →"}
            </button>
          </section>
        )}

        {done && sessionId && (
          <section className="card done">
            <h2>🎉 Review complete</h2>
            <p>
              You mastered {masteredCount} of {concepts.length} concepts. Your notes focus on the spots
              you found hardest.
            </p>
            <Link className="btn primary" href={`/session/${encodeURIComponent(sessionId)}/notes`}>
              See my notes and flashcards →
            </Link>
          </section>
        )}
      </div>

      <div className="study-right">
        <section className="card">
          <div className="card-head">
            <h3>Mastery map</h3>
            <span className="muted">Updates after every answer</span>
          </div>
          {concepts.length > 0 ? (
            <MasteryMap concepts={concepts} mastery={mastery} activeConceptId={current?.concept_id} />
          ) : (
            <p className="muted">Loading concepts…</p>
          )}
        </section>
        <TracePanel events={events} />
      </div>
    </div>
  );
}
