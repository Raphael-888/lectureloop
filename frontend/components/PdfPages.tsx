"use client";

// The "original PDF" view: slide pages stacked vertically, built from each page's text layer.
// (Page images are not served yet; see docs/api-contract.md §2b.)

import type { LecturePage } from "@/lib/types";

interface Props {
  pages: LecturePage[];
  highlight?: Set<string>; // concept ids: pages teaching them get an accent border
  nameOf: (conceptId: string) => string;
  loading?: boolean;
}

export default function PdfPages({ pages, highlight, nameOf, loading }: Props) {
  if (loading) {
    return (
      <p className="status">
        <span className="spinner" /> Loading slides…
      </p>
    );
  }
  if (pages.length === 0) return <p className="muted">No pages to show.</p>;

  return (
    <div className="pdf-stack">
      {pages.map((p) => {
        const hit = highlight && p.concept_ids.some((id) => highlight.has(id));
        const lines = p.text.split("\n").filter((l) => l.trim());
        const body = p.title && lines[0]?.trim() === p.title.trim() ? lines.slice(1) : lines;
        return (
          <article key={p.page} className={`pdf-sheet ${hit ? "hit" : ""}`}>
            <div className="pdf-sheet-head">
              <span>Page {p.page}</span>
              {p.concept_ids.length > 0 && (
                <span className="muted">{p.concept_ids.map(nameOf).join(" · ")}</span>
              )}
            </div>
            <div className="pdf-sheet-title">{p.title || `Slide ${p.page}`}</div>
            {body.slice(0, 14).map((l, i) => (
              <p key={i} className="pdf-sheet-line">
                {l}
              </p>
            ))}
          </article>
        );
      })}
    </div>
  );
}
