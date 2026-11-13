"use client";

// The "exploded" main page: every concept is a box scattered over the page, coloured by how
// well the student knows it. Click to select; the confirm bar appears below.
// Layout is deterministic (hash of the concept id), so the page looks the same on every visit.

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
    <div className="cloud" style={{ height: `${rows * 150 + 40}px` }}>
      {shuffled.map((c, i) => {
        const col = i % cols;
        const row = Math.floor(i / cols);
        const jx = (hash(c.id + "x") - 0.5) * 0.5; // ±25% of a cell
        const jy = (hash(c.id + "y") - 0.5) * 0.5;
        const left = ((col + 0.5 + jx) / cols) * 100;
        const top = ((row + 0.5 + jy) / rows) * 100;
        const rot = (hash(c.id + "r") - 0.5) * 6; // ±3°
        const label = mastery[c.id]?.label ?? "untested";
        const on = selected.has(c.id);
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
            <span className="cloud-name">{c.name}</span>
            <span className="cloud-meta">
              p. {c.pages[0]} · {LABEL_TEXT[label]}
            </span>
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
