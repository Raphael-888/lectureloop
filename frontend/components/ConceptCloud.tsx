"use client";

// The "exploded" main page, spatial-canvas style: every concept is a sheet of paper scattered
// over the canvas. Reviewed concepts get a coloured sticky note stuck on the sheet
// (pink = needs work, green = getting there, blue = mastered). Click to select.
// Layout is deterministic (hash of the concept id), so the canvas looks the same on every visit.

import type { Concept, Mastery, MasteryLabel } from "@/lib/types";

export const LABEL_TEXT: Record<MasteryLabel, string> = {
  untested: "Not reviewed",
  not_mastered: "Needs work",
  confused: "Getting there",
  mastered: "Mastered",
};

function hash(str: string): number {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) / 4294967295; // 0..1
}

interface Props {
  concepts: Concept[];
  mastery: Record<string, Mastery>;
  selected: Set<string>;
  onToggle: (id: string) => void;
  disabled?: boolean;
  animate?: boolean; // the "explosion" on first render
}

export default function ConceptCloud({ concepts, mastery, selected, onToggle, disabled, animate }: Props) {
  const n = concepts.length;
  const cols = Math.max(2, Math.min(5, Math.ceil(Math.sqrt(n * 1.5))));
  const rows = Math.max(1, Math.ceil(n / cols));
  // shuffle deterministically so slide order does not read as a straight line
  const shuffled = [...concepts].sort((a, b) => hash(a.id) - hash(b.id));

  return (
    <div className="cloud" style={{ height: `${rows * 250 + 60}px` }}>
      {shuffled.map((c, i) => {
        const col = i % cols;
        const row = Math.floor(i / cols);
        const jx = (hash(c.id + "x") - 0.5) * 0.3; // ±15% of a cell
        const jy = (hash(c.id + "y") - 0.5) * 0.3;
        const left = ((col + 0.5 + jx) / cols) * 100;
        const top = ((row + 0.5 + jy) / rows) * 100;
        const rot = (hash(c.id + "r") - 0.5) * 4; // ±2°
        const srot = (hash(c.id + "s") - 0.5) * 10; // sticky note tilt
        const label = mastery[c.id]?.label ?? "untested";
        const on = selected.has(c.id);
        const pages = c.pages.length > 1 ? `pp. ${c.pages[0]}–${c.pages[c.pages.length - 1]}` : `p. ${c.pages[0]}`;
        return (
          <button
            key={c.id}
            type="button"
            className={`cloud-box m-${label} ${on ? "on" : ""} ${animate ? "burst" : ""}`}
            style={
              {
                left: `${left}%`,
                top: `${top}%`,
                "--rot": `${rot}deg`,
                "--srot": `${srot}deg`,
                "--dx": `${50 - left}%`,
                "--dy": `${50 - top}%`,
                "--delay": `${(i / n) * 0.35}s`,
              } as React.CSSProperties
            }
            disabled={disabled}
            aria-pressed={on}
            title={c.summary}
            onClick={() => onToggle(c.id)}
          >
            <span className="cloud-check" aria-hidden="true">
              {on ? "✓" : ""}
            </span>
            <span className="cloud-name">
              <span className="hl">{c.name}</span>
            </span>
            <span className="cloud-meta">
              {pages}
              {label === "untested" ? " · not reviewed" : ""}
            </span>
            {c.summary && <span className="cloud-body">{c.summary}</span>}
            {label !== "untested" && (
              <span className={`cloud-sticky s-${label}`} aria-label={LABEL_TEXT[label]}>
                <i /> {LABEL_TEXT[label]}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export function CloudLegend() {
  return (
    <div className="legend">
      {(["untested", "not_mastered", "confused", "mastered"] as MasteryLabel[]).map((l) => (
        <span key={l}>
          <i className={`swatch m-${l}`} /> {LABEL_TEXT[l]}
        </span>
      ))}
    </div>
  );
}
