"use client";

// The "exploded" main page, spatial-canvas style: every concept is a sheet of paper scattered
// over the canvas. Reviewed concepts get a coloured sticky note stuck on the sheet
// (pink = needs work, green = getting there, blue = mastered). Click to select.
// Layout is deterministic (hash of the concept id), so the canvas looks the same on every visit.
// Arrows under the sheets show the prerequisite graph (prerequisite -> concept that builds on it).
// Hovering or selecting a concept highlights its own arrows and fades the rest.

import { useCallback, useId, useLayoutEffect, useRef, useState } from "react";
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

// Card geometry in px, from offsetLeft/offsetTop. The sheets are centred on their left/top point
// with a CSS transform, and offset* ignore transforms, so (x, y) is the centre of the sheet even
// while it is rotated, scaled on hover, or still flying in.
interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

const GAP = 8; // px between an arrow's end and the edge of a sheet

/** Point where the ray from the centre of `b` towards (tx, ty) leaves the sheet, plus a small gap. */
function edgePoint(b: Box, tx: number, ty: number): [number, number] {
  const dx = tx - b.x;
  const dy = ty - b.y;
  const len = Math.hypot(dx, dy) || 1;
  const t = Math.min(dx ? b.w / 2 / Math.abs(dx) : Infinity, dy ? b.h / 2 / Math.abs(dy) : Infinity);
  return [b.x + dx * t + (dx / len) * GAP, b.y + dy * t + (dy / len) * GAP];
}

/** A gently curved path from prerequisite `a` to concept `b`, clipped to the sheet edges. */
function arrowPath(a: Box, b: Box): string | null {
  const [x1, y1] = edgePoint(a, b.x, b.y);
  const [x2, y2] = edgePoint(b, a.x, a.y);
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.hypot(dx, dy);
  // the sheets touch or overlap: an arrow would point the wrong way, so draw none
  if (len < 24 || dx * (b.x - a.x) + dy * (b.y - a.y) <= 0) return null;
  const bend = Math.min(40, len * 0.12);
  const cx = (x1 + x2) / 2 - (dy / len) * bend;
  const cy = (y1 + y2) / 2 + (dx / len) * bend;
  return `M ${x1.toFixed(1)} ${y1.toFixed(1)} Q ${cx.toFixed(1)} ${cy.toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)}`;
}

export default function ConceptCloud({ concepts, mastery, selected, onToggle, disabled, animate }: Props) {
  const cloudRef = useRef<HTMLDivElement>(null);
  const boxRefs = useRef(new Map<string, HTMLButtonElement>());
  const [boxes, setBoxes] = useState<Record<string, Box>>({});
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [hovered, setHovered] = useState<string | null>(null);
  const markerId = useId().replace(/:/g, "");

  const measure = useCallback(() => {
    const cloud = cloudRef.current;
    if (!cloud) return;
    const next: Record<string, Box> = {};
    boxRefs.current.forEach((el, id) => {
      next[id] = { x: el.offsetLeft, y: el.offsetTop, w: el.offsetWidth, h: el.offsetHeight };
    });
    setBoxes(next);
    setSize({ w: cloud.clientWidth, h: cloud.clientHeight });
  }, []);

  useLayoutEffect(() => {
    measure();
    const cloud = cloudRef.current;
    if (!cloud || typeof ResizeObserver === "undefined") return;
    // the canvas width changes with the window; sheet heights change when fonts load
    const ro = new ResizeObserver(measure);
    ro.observe(cloud);
    boxRefs.current.forEach((el) => ro.observe(el));
    return () => ro.disconnect();
  }, [measure, concepts]);

  const known = new Set(concepts.map((c) => c.id));
  const focus = new Set<string>(selected);
  if (hovered) focus.add(hovered);
  const edges = concepts.flatMap((c) =>
    c.prerequisites
      .filter((p) => known.has(p) && p !== c.id)
      .map((p) => ({ from: p, to: c.id, active: focus.has(p) || focus.has(c.id) })),
  );
  const dim = focus.size > 0;

  const n = concepts.length;
  const cols = Math.max(2, Math.min(5, Math.ceil(Math.sqrt(n * 1.5))));
  const rows = Math.max(1, Math.ceil(n / cols));
  // shuffle deterministically so slide order does not read as a straight line
  const shuffled = [...concepts].sort((a, b) => hash(a.id) - hash(b.id));

  return (
    <div ref={cloudRef} className="cloud" style={{ height: `${rows * 250 + 60}px` }}>
      {size.w > 0 && (
        <svg
          className={`cloud-links ${animate ? "burst" : ""}`}
          width={size.w}
          height={size.h}
          viewBox={`0 0 ${size.w} ${size.h}`}
          aria-hidden="true"
        >
          <defs>
            {["idle", "active"].map((kind) => (
              <marker
                key={kind}
                id={`${markerId}-${kind}`}
                className={`cloud-arrowhead ${kind}`}
                viewBox="0 0 10 10"
                refX="9"
                refY="5"
                markerWidth="7"
                markerHeight="7"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" />
              </marker>
            ))}
          </defs>
          {/* draw the highlighted arrows last so they sit on top of the faded ones */}
          {[...edges]
            .sort((a, b) => Number(a.active) - Number(b.active))
            .map((e) => {
              const a = boxes[e.from];
              const b = boxes[e.to];
              const d = a && b ? arrowPath(a, b) : null;
              if (!d) return null;
              const kind = e.active ? "active" : "idle";
              return (
                <path
                  key={`${e.from}->${e.to}`}
                  d={d}
                  className={`cloud-link ${kind} ${dim && !e.active ? "faded" : ""}`}
                  markerEnd={`url(#${markerId}-${kind})`}
                />
              );
            })}
        </svg>
      )}
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
            ref={(el) => {
              if (el) boxRefs.current.set(c.id, el);
              else boxRefs.current.delete(c.id);
            }}
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
            onMouseEnter={() => setHovered(c.id)}
            onMouseLeave={() => setHovered((h) => (h === c.id ? null : h))}
            onFocus={() => setHovered(c.id)}
            onBlur={() => setHovered((h) => (h === c.id ? null : h))}
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
      <span>
        <i className="legend-arrow" aria-hidden="true" /> learn first → builds on it
      </span>
    </div>
  );
}
