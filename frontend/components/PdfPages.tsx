"use client";

// The "original PDF" view: one card per slide page, built from the page's text layer.
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
    <div className="pdf-grid">
      {pages.map((p) => {
        const hit = highlight && p.concept_ids.some((id) => highlight.has(id));
        const lines = p.text.split("\n").filter((l) => l.trim()).slice(0, 6);
        return (
          <article key={p.page} className={`pdf-page ${hit ? "hit" : ""}`}>
            <div className="pdf-page-paper">
              <div className="pdf-page-title">{p.title || `Slide ${p.page}`}</div>
              {lines.slice(p.title ? 1 : 0).map((l, i) => (
                <div key={i} className="pdf-page-line">
                  {l}
                </div>
              ))}
            </div>
            <div className="pdf-page-meta">
              <span>Page {p.page}</span>
              {p.concept_ids.length > 0 && (
                <span className="muted" title={p.concept_ids.map(nameOf).join(", ")}>
                  {p.concept_ids.length === 1 ? nameOf(p.concept_ids[0]) : `${p.concept_ids.length} concepts`}
                </span>
              )}
            </div>
          </article>
        );
      })}
    </div>
  );
}
