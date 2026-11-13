"use client";

// Page 5: personalised notes + flashcards + Anki export.

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import FlashcardDeck from "@/components/FlashcardDeck";
import Markdown from "@/components/Markdown";
import * as api from "@/lib/api";
import type { NotesResponse } from "@/lib/types";

const pretty = (id: string) => id.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

export default function NotesPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [notes, setNotes] = useState<NotesResponse | null>(null);
  const [lectureId, setLectureId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getNotes(sessionId)
      .then((n) => !cancelled && setNotes(n))
      .catch((e) => !cancelled && setError(api.errorMessage(e)));
    api
      .getSession(sessionId)
      .then((s) => !cancelled && setLectureId(s.lecture_id))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  async function downloadCsv() {
    try {
      const url = await api.getFlashcardsCsvUrl(sessionId);
      const a = document.createElement("a");
      a.href = url;
      a.download = "lectureloop-flashcards.csv";
      a.click();
    } catch (e) {
      setError(api.errorMessage(e));
    }
  }

  if (error) return <p className="error narrow">{error}</p>;
  if (!notes)
    return (
      <p className="status narrow">
        <span className="spinner" /> Writing your notes…
      </p>
    );

  const weak = new Set(notes.weak_concepts);

  return (
    <div className="notes-layout">
      <section className="card notes">
        {notes.weak_concepts.length > 0 && (
          <div className="weak-box">
            <strong>Review these first:</strong>
            <ul className="chips">
              {notes.weak_concepts.map((id) => (
                <li key={id} className="warn">
                  {pretty(id)}
                </li>
              ))}
            </ul>
          </div>
        )}
        <Markdown>{notes.summary_markdown}</Markdown>
      </section>

      <aside className="notes-side">
        <section className="card">
          <div className="card-head">
            <h3>Flashcards</h3>
            <span className="muted">Weak spots first</span>
          </div>
          <FlashcardDeck cards={notes.flashcards} weak={weak} />
          <button className="btn wide" onClick={downloadCsv}>
            ⬇ Export to Anki (CSV)
          </button>
        </section>
        {lectureId && (
          <Link className="btn wide" href={`/lecture/${encodeURIComponent(lectureId)}`}>
            Back to all concepts
          </Link>
        )}
        <Link className="btn wide" href="/">
          Upload another lecture
        </Link>
      </aside>
    </div>
  );
}
