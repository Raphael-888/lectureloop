"use client";

// Page 3: pick concepts. Left: concept map / original PDF. Right: the review box.
// After "Submit selection" a session is created on the backend: its summary and the tutor chat
// appear on the right, and "Next" goes to the quiz.

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import ConceptBlocks from "@/components/ConceptBlocks";
import Markdown from "@/components/Markdown";
import PdfPages from "@/components/PdfPages";
import ReviewBox from "@/components/ReviewBox";
import StepBar from "@/components/StepBar";
import TutorChat from "@/components/TutorChat";
import * as api from "@/lib/api";
import { useLecture } from "@/lib/useLecture";
import type { LecturePage, SessionState } from "@/lib/types";

type View = "map" | "pdf";

export default function ReviewPage() {
  const { lectureId } = useParams<{ lectureId: string }>();
  const { lecture, concepts, blocks, nameOf, error: lectureError } = useLecture(lectureId);

  const [view, setView] = useState<View>("map");
  const [selected, setSelected] = useState<string[]>([]);
  const [pages, setPages] = useState<LecturePage[]>([]);
  const [pagesLoading, setPagesLoading] = useState(false);
  const [session, setSession] = useState<SessionState | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitted = session !== null;
  const scope = submitted ? session.concept_ids : [];

  // slide pages: all of them, or only the selected concepts' pages once submitted
  useEffect(() => {
    if (!lecture) return;
    let cancelled = false;
    setPagesLoading(true);
    api
      .getPages(lectureId, scope)
      .then((r) => !cancelled && setPages(r.pages))
      .catch((e) => !cancelled && setError(api.errorMessage(e)))
      .finally(() => !cancelled && setPagesLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lectureId, lecture, scope.join(",")]);

  function add(id: string) {
    if (submitted || !concepts.some((c) => c.id === id)) return;
    setSelected((s) => (s.includes(id) ? s : [...s, id]));
  }
  function remove(id: string) {
    if (submitted) return;
    setSelected((s) => s.filter((x) => x !== id));
  }
  function toggle(id: string) {
    if (submitted) return;
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }

  async function submit() {
    if (selected.length === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      const r = await api.startSession(lectureId, selected);
      setSession(await api.getSession(r.session_id));
    } catch (e) {
      setError(api.errorMessage(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function send(message: string) {
    if (!session) return;
    try {
      await api.chat(session.session_id, message);
      setSession(await api.getSession(session.session_id));
    } catch (e) {
      setError(api.errorMessage(e));
    }
  }

  if (lectureError) return <p className="error narrow">{lectureError}</p>;
  if (!lecture) {
    return (
      <p className="status narrow">
        <span className="spinner" /> Loading the lecture…
      </p>
    );
  }

  const selectedSet = new Set(selected);
  const count = selected.length;

  return (
    <div className="page wide">
      <div className="page-head">
        <div>
          <Link href={`/lecture/${encodeURIComponent(lectureId)}`} className="backlink">
            ← Overview
          </Link>
          <h1>{lecture.title || "Your lecture"}</h1>
        </div>
        <StepBar current={3} />
      </div>

      {error && <p className="error">{error}</p>}

      <div className="split">
        {/* LEFT */}
        <section className="card left-pane">
          <div className="card-head">
            <div>
              <h3>{view === "map" ? "Concept map" : "Lecture slides"}</h3>
              <span className="muted">
                {view === "map"
                  ? `${blocks.length} topics · ${concepts.length} concepts, in lecture order`
                  : submitted
                    ? `${pages.length} of ${lecture.page_count ?? "?"} pages match your selection`
                    : `${lecture.page_count ?? pages.length} pages`}
              </span>
            </div>
            <div className="segmented" role="group" aria-label="View">
              <button type="button" className={view === "map" ? "on" : ""} onClick={() => setView("map")}>
                Mind map
              </button>
              <button type="button" className={view === "pdf" ? "on" : ""} onClick={() => setView("pdf")}>
                Original PDF
              </button>
            </div>
          </div>

          {view === "map" ? (
            <>
              <ConceptBlocks blocks={blocks} variant="pick" selected={selectedSet} onToggle={toggle} disabled={submitted} />
              <p className="muted hint-line">
                Drag a concept into the box on the right, or click it. Pick one or several: the order of the slides
                doesn&apos;t matter when you review.
              </p>
            </>
          ) : (
            <>
              <p className="muted hint-line">
                {submitted ? "Only the pages that teach the concepts you picked." : "All pages. Submit a selection to narrow this down."}
              </p>
              <PdfPages pages={pages} highlight={new Set(scope)} nameOf={nameOf} loading={pagesLoading} />
            </>
          )}
        </section>

        {/* RIGHT */}
        <aside className="right-pane">
          <ReviewBox
            selected={selected}
            nameOf={nameOf}
            onAdd={add}
            onRemove={remove}
            onSubmit={submit}
            onReset={() => setSession(null)}
            submitted={submitted}
            submitting={submitting}
          />

          {session && (
            <>
              <section className="card">
                <div className="eyebrow">✦ AI summary</div>
                <h3 className="summary-title">{count === 1 ? nameOf(selected[0]) : `${count} concepts, one review`}</h3>
                <Markdown>{session.scope_summary}</Markdown>
                <p className="muted">
                  The <button type="button" className="linklike" onClick={() => setView("pdf")}>Original PDF</button> view now shows
                  only the pages for these concepts.
                </p>
              </section>

              <TutorChat
                compact
                title="Before you start"
                intro="Anything unclear before we start? Ask me here, or hit Next and I'll quiz you."
                messages={session.chat}
                onSend={send}
                placeholder="e.g. why is the cost a convex bowl?"
              />

              <Link className="btn primary wide big" href={`/session/${encodeURIComponent(session.session_id)}`}>
                Next: quiz me on {count === 1 ? "this concept" : `${count} concepts`} →
              </Link>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
