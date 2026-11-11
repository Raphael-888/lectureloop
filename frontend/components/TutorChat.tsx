"use client";

// One chat box, two jobs: ask about the material, or tell the tutor how to quiz you.

import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "@/lib/types";

interface Props {
  messages: ChatMessage[];
  intro: string; // the tutor's opening line (not stored on the server)
  onSend: (message: string) => Promise<void>;
  suggestions?: string[];
  placeholder?: string;
  title?: string;
  compact?: boolean;
}

export default function TutorChat({ messages, intro, onSend, suggestions = [], placeholder, title = "Tutor", compact }: Props) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages.length, busy]);

  async function send(message: string) {
    const m = message.trim();
    if (!m || busy) return;
    setText("");
    setBusy(true);
    try {
      await onSend(m);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={`card chat ${compact ? "compact" : ""}`} aria-label={title}>
      <div className="card-head">
        <h3>{title}</h3>
        <span className="muted">Ask, or change how it quizzes you</span>
      </div>

      <div ref={listRef} className="chat-list">
        <Bubble role="tutor" text={intro} />
        {messages.map((m, i) => (
          <Bubble key={i} role={m.role} text={m.text} />
        ))}
        {busy && <Bubble role="tutor" text="…" />}
      </div>

      {suggestions.length > 0 && (
        <div className="chat-suggest">
          {suggestions.map((s) => (
            <button key={s} type="button" className="btn tiny" disabled={busy} onClick={() => send(s)}>
              {s}
            </button>
          ))}
        </div>
      )}

      <form
        className="chat-form"
        onSubmit={(e) => {
          e.preventDefault();
          send(text);
        }}
      >
        <label htmlFor={`chat-${title}`} className="sr-only">
          Message the tutor
        </label>
        <input
          id={`chat-${title}`}
          type="text"
          value={text}
          disabled={busy}
          placeholder={placeholder ?? "Ask anything, or say how to change the quiz"}
          onChange={(e) => setText(e.target.value)}
        />
        <button type="submit" className="btn primary" aria-label="Send" disabled={busy || !text.trim()}>
          →
        </button>
      </form>
    </section>
  );
}

function Bubble({ role, text }: { role: ChatMessage["role"]; text: string }) {
  return (
    <div className={`bubble-row ${role}`}>
      {role === "tutor" && <span className="avatar">↻</span>}
      <div className="bubble">{text}</div>
    </div>
  );
}
