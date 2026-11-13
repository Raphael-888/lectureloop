"use client";

// The question-type / difficulty picker on the quiz page (top right). The chat can do the
// same in words; this is the one-click version from the Nov 12 sketch.

import { useEffect, useRef, useState } from "react";
import type { Difficulty, Preferences, PreferencesUpdate, QuestionType } from "@/lib/types";

interface Props {
  prefs: Preferences;
  onChange: (update: PreferencesUpdate) => Promise<void>;
}

const TYPES: { key: QuestionType | "agent"; label: string }[] = [
  { key: "agent", label: "Let the tutor decide" },
  { key: "multiple_choice", label: "Multiple choice" },
  { key: "short_answer", label: "Short answer" },
];
const LEVELS: { key: Difficulty; label: string }[] = [
  { key: "easier", label: "Easier" },
  { key: "same", label: "Normal" },
  { key: "harder", label: "Harder" },
];

export default function QuizSettings({ prefs, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener("mousedown", close);
    return () => window.removeEventListener("mousedown", close);
  }, [open]);

  async function apply(update: PreferencesUpdate) {
    setBusy(true);
    try {
      await onChange(update);
    } finally {
      setBusy(false);
    }
  }

  const typeLabel = TYPES.find((t) => t.key === (prefs.question_type ?? "agent"))!.label;
  const levelLabel = LEVELS.find((l) => l.key === prefs.difficulty)!.label;

  return (
    <div className="menu" ref={ref}>
      <button type="button" className="btn" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-haspopup="menu">
        ⚙ {typeLabel} · {levelLabel} ▾
      </button>
      {open && (
        <div className="menu-panel" role="menu">
          <div className="menu-title">Question type</div>
          {TYPES.map((t) => (
            <label key={t.key} className="menu-item">
              <input
                type="radio"
                name="qtype"
                disabled={busy}
                checked={(prefs.question_type ?? "agent") === t.key}
                onChange={() => apply(t.key === "agent" ? { clear_question_type: true } : { question_type: t.key })}
              />
              {t.label}
            </label>
          ))}
          <div className="menu-title">Difficulty</div>
          {LEVELS.map((l) => (
            <label key={l.key} className="menu-item">
              <input
                type="radio"
                name="level"
                disabled={busy}
                checked={prefs.difficulty === l.key}
                onChange={() => apply({ difficulty: l.key })}
              />
              {l.label}
            </label>
          ))}
          <div className="muted menu-foot">Applies from the next question.</div>
        </div>
      )}
    </div>
  );
}
