"use client";

// Two panes with a draggable divider (the review page's PDF split view).

import { useCallback, useRef, useState, type ReactNode } from "react";

interface Props {
  left: ReactNode;
  right: ReactNode;
  initial?: number; // left pane width in %
}

export default function SplitPane({ left, right, initial = 50 }: Props) {
  const [pct, setPct] = useState(initial);
  const ref = useRef<HTMLDivElement>(null);

  const startDrag = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const move = (ev: PointerEvent) => {
      const p = ((ev.clientX - rect.left) / rect.width) * 100;
      setPct(Math.min(75, Math.max(25, p)));
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }, []);

  return (
    <div ref={ref} className="splitpane" style={{ gridTemplateColumns: `${pct}% 10px minmax(0, 1fr)` }}>
      <div className="splitpane-left">{left}</div>
      <div
        className="splitpane-divider"
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize"
        onPointerDown={startDrag}
      />
      <div className="splitpane-right">{right}</div>
    </div>
  );
}
