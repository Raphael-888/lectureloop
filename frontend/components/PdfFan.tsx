"use client";

// The review page's PDF button: the first three slides for the selected concepts, fanned out
// like photos on a table. Clicking anywhere on it opens the slides beside the summary.

import { PageImage } from "./PdfPages";
import type { LecturePage } from "@/lib/types";

interface Props {
  lectureId: string;
  pages: LecturePage[] | null; // null while loading
  conceptCount: number;
  onOpen: () => void;
}

export default function PdfFan({ lectureId, pages, conceptCount, onOpen }: Props) {
  const shown = (pages ?? []).slice(0, 3);
  return (
    <button type="button" className="pdf-fan" onClick={onOpen} aria-label="Open the slides">
      <span className="fan-stack" aria-hidden="true">
        {pages === null
          ? [0, 1, 2].map((i) => <span key={i} className="fan-card blank" />)
          : shown.map((p) => (
              <span key={p.page} className="fan-card">
                <PageImage lectureId={lectureId} page={p} small />
              </span>
            ))}
      </span>
      <span className="fan-caption">
        {pages === null
          ? "Finding the slides…"
          : `${pages.length} slide${pages.length === 1 ? "" : "s"} for ${conceptCount === 1 ? "this concept" : "these concepts"}`}
      </span>
      <span className="fan-cta">Open the PDF →</span>
    </button>
  );
}
