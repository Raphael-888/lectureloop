"use client";

// Page 2: the main page, a spatial canvas. The lecture's concepts "explode" over the page, coloured by how well
// the student knows each one. Click the ones to review, confirm, and a session starts.

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import BookmarksDrawer from "@/components/BookmarksDrawer";
import ConceptCloud, { CloudLegend } from "@/components/ConceptCloud";
import StepBar from "@/components/StepBar";
import * as api from "@/lib/api";
import { useLecture } from "@/lib/useLecture";
import type { BookmarkItem, Mastery } from "@/lib/types";

export default function ConceptsPage() {
  const { lectureId } = useParams<{ lectureId: string }>();
  const router = useRouter();
  const { lecture, concepts, nameOf, error: lectureError } = useLecture(lectureId);

  const [mastery, setMastery] = useState<Record<string, Mastery>>({});
  const [sessionsSoFar, setSessionsSoFar] = useState(0);
  const [selected, setSelected] = useState<string[]>([]);
  const [starting, setStarting] = useState(false);
  const [bookmarks, setBookmarks] = useState<BookmarkItem[]>([]);
  const [drawer, setDrawer] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [m, b] = await Promise.all([api.getLectureMastery(lectureId), api.getBookmarks(lectureId)]);
      setMastery(Object.fromEntries(m.mastery.map((x) => [x.concept_id, x])));
      setSessionsSoFar(m.sessions);
      setBookmarks(b.items);
    } catch (e) {
      setError(api.errorMessage(e));
    }
  }, [lectureId]);

  useEffect(() => {
    if (lecture) refresh();
  }, [lecture, refresh]);

  function toggle(id: string) {
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }

  async function confirm(ids: string[]) {
    if (ids.length === 0) return;
    setStarting(true);
    setError(null);
    try {
      const r = await api.startSession(lectureId, ids);
      router.push(`/session/${encodeURIComponent(r.session_id)}`);
    } catch (e) {
      setError(api.errorMessage(e));
      setStarting(false);
    }
  }

  async function removeBookmark(item: BookmarkItem) {
    try {
      const r = await api.toggleBookmark(lectureId, item.question.id, item.session_id);
      setBookmarks(r.items);
    } catch (e) {
      setError(api.errorMessage(e));
    }
  }

  if (lectureError) return <p className="error narrow">{lectureError}</p>;
  if (!lecture) {
    return (
      <p className="status narrow">
        <span className="spinner" /> Reading the slides and mapping concepts…
      </p>
    );
  }

  const counts = { mastered: 0, confused: 0, not_mastered: 0, untested: 0 };
  for (const c of concepts) counts[mastery[c.id]?.label ?? "untested"] += 1;

  return (
    <div className="board">
      <div className="board-head">
        <div>
          <div className="eyebrow">{lecture.page_count ?? "?"} slides · {concepts.length} concepts</div>
          <h1>{lecture.title || "Your lecture"}</h1>
          <span className="board-sub">
            {sessionsSoFar === 0
              ? "Pick one sheet for a focused drill, several for a mixed review. Sticky notes appear as you quiz yourself."
              : `${counts.mastered} mastered · ${counts.confused} getting there · ${counts.not_mastered} need work · ${counts.untested} not reviewed`}
          </span>
        </div>
        <div className="board-tools">
          <StepBar current={2} />
          <CloudLegend />
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      <ConceptCloud
        concepts={concepts}
        mastery={mastery}
        selected={new Set(selected)}
        onToggle={toggle}
        disabled={starting}
        animate={sessionsSoFar === 0}
      />

      <div className="dock" role="toolbar" aria-label="Concept actions">
        {selected.length === 0 ? (
          <>
            <span className="dock-hint">Click the concepts you want to review</span>
            <span className="dock-sep" aria-hidden="true" />
            <button type="button" className="dock-btn" onClick={() => setDrawer(true)} title="Saved questions">
              ★<span>Saved{bookmarks.length ? ` (${bookmarks.length})` : ""}</span>
            </button>
            <Link href="/" className="dock-btn" title="Upload another lecture">
              ＋<span>New lecture</span>
            </Link>
          </>
        ) : (
          <>
            <span className="dock-text">
              <strong>
                Review {selected.length} concept{selected.length === 1 ? "" : "s"}
              </strong>
              <span>{selected.map(nameOf).join(" · ")}</span>
            </span>
            <span className="dock-sep" aria-hidden="true" />
            <button type="button" className="dock-btn" disabled={starting} onClick={() => setSelected([])}>
              Clear
            </button>
            <button type="button" className="dock-btn go" disabled={starting} onClick={() => confirm(selected)}>
              {starting ? "Preparing…" : "Confirm →"}
            </button>
          </>
        )}
      </div>

      <BookmarksDrawer
        open={drawer}
        items={bookmarks}
        onClose={() => setDrawer(false)}
        onReview={(conceptId) => {
          setDrawer(false);
          confirm([conceptId]);
        }}
        onRemove={removeBookmark}
      />
    </div>
  );
}
