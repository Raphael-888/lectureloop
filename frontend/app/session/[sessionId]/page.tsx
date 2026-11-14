"use client";

// Page 3: the review page for the selected concepts. Title "A & B", the AI summary top left,
// the tutor chat below it, the slides fanned out on the right (click to open them as the PDF
// pages in a split view), and "Start quiz" in the dock at the bottom.

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import Markdown from "@/components/Markdown";
import PdfFan from "@/components/PdfFan";
import PdfPages from "@/components/PdfPages";
import SplitPane from "@/components/SplitPane";
import StepBar from "@/components/StepBar";
import TutorChat from "@/components/TutorChat";
import * as api from "@/lib/api";
import type { Concept, LecturePage, SessionState } from "@/lib/types";

export default function ReviewPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const router = useRouter();
  const [state, setState] = useState<SessionState | null>(null);
  const [starting, setStarting] = useState(false);
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [pages, setPages] = useState<LecturePage[] | null>(null);
  const [showPdf, setShowPdf] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nameOf = useMemo(() => {
    const names = new Map(concepts.map((c) => [c.id, c.name]));
    return (id: string) => names.get(id) ?? id;
  }, [concepts]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = await api.getSession(sessionId);
        if (cancelled) return;
        setState(s);
        const c = await api.getConcepts(s.lecture_id);
        if (!cancelled) setConcepts(c.concepts);
      } catch (e) {
        if (!cancelled) setError(api.errorMessage(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  // load the slides up front: the fan on the right shows the first three
  useEffect(() => {
    if (pages !== null || !state) return;
    api
      .getPages(state.lecture_id, state.concept_ids)
      .then((r) => setPages(r.pages))
      .catch((e) => setError(api.errorMessage(e)));
  }, [pages, state]);

  async function send(message: string) {
    try {
      await api.chat(sessionId, message);
      setState(await api.getSession(sessionId));
    } catch (e) {
      setError(api.errorMessage(e));
    }
  }

  // A finished session cannot be quizzed again: start a fresh one on the same concepts.
  async function startQuiz() {
    if (!state) return;
    if (!state.done) return router.push(`/session/${encodeURIComponent(sessionId)}/quiz`);
    setStarting(true);
    try {
      const r = await api.startSession(state.lecture_id, state.concept_ids);
      router.push(`/session/${encodeURIComponent(r.session_id)}/quiz`);
    } catch (e) {
      setError(api.errorMessage(e));
      setStarting(false);
    }
  }

  if (error && !state) return <p className="error narrow">{error}</p>;
  if (!state) {
    return (
      <p className="status narrow">
        <span className="spinner" /> Preparing your review…
      </p>
    );
  }

  const title = state.concept_ids.map(nameOf).join(" & ");

  const summary = (
    <section className="card review-summary">
      <div className="eyebrow">✦ AI summary</div>
      <Markdown>{state.scope_summary}</Markdown>
    </section>
  );
  const chat = (
    <div className="review-chat">
      <TutorChat
        title="Ask before you start"
        intro="Anything unclear? Ask me here. When you're ready, start the quiz and I'll test exactly these concepts."
        messages={state.chat}
        onSend={send}
        placeholder="e.g. why is the cost a convex bowl?"
      />
    </div>
  );

  return (
    <div className="page wide">
      <div className="page-head">
        <div>
          <Link href={`/lecture/${encodeURIComponent(state.lecture_id)}`} className="backlink">
            ← All concepts
          </Link>
          <h1>{title}</h1>
        </div>
        <StepBar current={3} />
      </div>

      {error && <p className="error">{error}</p>}

      {showPdf ? (
        <SplitPane
          initial={52}
          left={
            <div className="review-left">
              {summary}
              {chat}
            </div>
          }
          right={
            <section className="card pdf-pane">
              <div className="card-head">
                <div>
                  <h3>Slides for {state.concept_ids.length === 1 ? "this concept" : "these concepts"}</h3>
                  <span className="muted">{pages ? `${pages.length} pages` : ""}</span>
                </div>
                <button type="button" className="btn tiny" onClick={() => setShowPdf(false)}>
                  Close ✕
                </button>
              </div>
              <PdfPages
                lectureId={state.lecture_id}
                pages={pages ?? []}
                highlight={new Set(state.concept_ids)}
                nameOf={nameOf}
                loading={pages === null}
              />
            </section>
          }
        />
      ) : (
        <div className="review-grid">
          <div className="review-left">
            {summary}
            {chat}
          </div>
          <div className="review-b">
            <PdfFan lectureId={state.lecture_id} pages={pages} conceptCount={state.concept_ids.length} onOpen={() => setShowPdf(true)} />
          </div>
        </div>
      )}

      <div className="cta-row sticky-cta">
        <span className="muted">
          {state.done ? "You already finished a quiz on this. Start another or go back." : "Ready?"}
        </span>
        <button type="button" className="btn primary big" disabled={starting} onClick={startQuiz}>
          {starting ? "Preparing…" : state.done ? "Quiz again →" : "Start quiz →"}
        </button>
      </div>
    </div>
  );
}
