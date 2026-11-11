"use client";

// The agent's tool calls, one per step. Hidden behind a disclosure on the quiz page
// (product decision, Nov 10) but kept: judges score visible agentic behaviour.

import { useEffect, useRef } from "react";
import type { TraceEvent } from "@/lib/types";

function clock(iso: string) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleTimeString([], { hour12: false });
}

export default function TracePanel({ events }: { events: TraceEvent[] }) {
  const listRef = useRef<HTMLOListElement>(null);

  // keep the newest step in view
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [events.length]);

  if (events.length === 0) return <p className="muted">Waiting for the agent…</p>;

  return (
    <ol ref={listRef} className="trace-list">
      {events.map((e) => (
        <li key={e.step} className="trace-item">
          <div className="trace-top">
            <span className="trace-step">#{e.step}</span>
            <code className={`tool tool-${e.tool}`}>{e.tool}</code>
            <span className="trace-time">{clock(e.time)}</span>
          </div>
          <div className="trace-reason">{e.reason}</div>
          <div className="trace-summary">→ {e.summary}</div>
        </li>
      ))}
    </ol>
  );
}
