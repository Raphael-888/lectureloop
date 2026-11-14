"use client";

// The "original PDF" view: slide pages stacked vertically, each shown as the PDF page itself
// (GET /api/lectures/{id}/pages/{page}/image). If the image is missing (mock mode, or an
// older lecture processed before images were kept) the page is drawn from its text layer.

import { useState } from "react";
import { pageImageUrl } from "@/lib/api";
import type { LecturePage } from "@/lib/types";

interface Props {
  lectureId: string;
  pages: LecturePage[];
  highlight?: Set<string>; // concept ids: pages teaching them get their names highlighted
  nameOf: (conceptId: string) => string;
  loading?: boolean;
}

export default function PdfPages({ lectureId, pages, highlight, nameOf, loading }: Props) {
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
        const hit = !!highlight && p.concept_ids.some((id) => highlight.has(id));
        return (
          <article key={p.page} className={`pdf-sheet image ${hit ? "hit" : ""}`}>
            <div className="pdf-sheet-head">
              <span>Page {p.page}</span>
              {p.concept_ids.length > 0 && (
                <span className={hit ? "hl" : "muted"}>{p.concept_ids.map(nameOf).join(" · ")}</span>
              )}
            </div>
            <PageImage lectureId={lectureId} page={p} />
          </article>
        );
      })}
    </div>
  );
}

/** The page as an image, or its text when there is no image. Also used by the PDF fan. */
export function PageImage({ lectureId, page, small }: { lectureId: string; page: LecturePage; small?: boolean }) {
  const url = pageImageUrl(lectureId, page.page);
  const [failed, setFailed] = useState(false);

  if (url && !failed) {
    // eslint-disable-next-line @next/next/no-img-element -- served by our own API, already sized
    return <img className="pdf-img" src={url} alt={`Slide ${page.page}: ${page.title}`} loading="lazy" onError={() => setFailed(true)} />;
  }

  const lines = page.text.split("\n").filter((l) => l.trim());
  const body = page.title && lines[0]?.trim() === page.title.trim() ? lines.slice(1) : lines;
  return (
    <div className={`pdf-text ${small ? "small" : ""}`}>
      <div className="pdf-sheet-title">{page.title || `Slide ${page.page}`}</div>
      {body.slice(0, small ? 5 : 14).map((l, i) => (
        <p key={i} className="pdf-sheet-line">
          {l}
        </p>
      ))}
    </div>
  );
}
