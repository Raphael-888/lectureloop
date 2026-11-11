"use client";

import { useState } from "react";
import type { Question } from "@/lib/types";

// "B. Bottom-up" -> "B" (the contract sends the option letter as the answer)
function optionLetter(option: string): string {
  const m = option.match(/^\s*([A-Za-z])[.)]\s/);
  return m ? m[1].toUpperCase() : option;
}

interface Props {
  question: Question;
  conceptName: string;
  locked: boolean; // true after submitting, until the student continues
  submitting: boolean;
  onSubmit: (answer: string) => void;
}

export default function QuestionCard({ question, conceptName, locked, submitting, onSubmit }: Props) {
  const [answer, setAnswer] = useState("");
  const disabled = locked || submitting;

  return (
    <form
      className="card"
      onSubmit={(e) => {
        e.preventDefault();
        if (answer.trim() && !disabled) onSubmit(answer);
      }}
    >
      <div className="eyebrow">{conceptName}</div>
      <h2 className="question-prompt">{question.prompt}</h2>

      {question.type === "multiple_choice" && question.options ? (
        <div className="options">
          {question.options.map((opt) => {
            const letter = optionLetter(opt);
            return (
              <label key={opt} className={`option ${answer === letter ? "selected" : ""}`}>
                <input
                  type="radio"
                  name={question.id}
                  value={letter}
                  checked={answer === letter}
                  disabled={disabled}
                  onChange={() => setAnswer(letter)}
                />
                <span>{opt}</span>
              </label>
            );
          })}
        </div>
      ) : (
        <textarea
          className="short-answer"
          rows={4}
          placeholder="Type your answer…"
          value={answer}
          disabled={disabled}
          onChange={(e) => setAnswer(e.target.value)}
        />
      )}

      {!locked && (
        <button className="btn primary" type="submit" disabled={!answer.trim() || submitting}>
          {submitting ? "Grading…" : "Submit answer"}
        </button>
      )}
    </form>
  );
}
