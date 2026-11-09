"use client";

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

  return (
    <section className="card trace">
      <div className="card-head">
        <h3>Agent trace</h3>
        <span className="muted">{events.length} steps · live</span>
      </div>
      {events.length === 0 ? (
        <p className="muted">Waiting for the agent…</p>
      ) : (
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
      )}
    </section>
  );
}
