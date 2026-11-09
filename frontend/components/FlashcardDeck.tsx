"use client";

import { useState } from "react";
import type { Flashcard } from "@/lib/types";

export default function FlashcardDeck({ cards, weak }: { cards: Flashcard[]; weak: Set<string> }) {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  if (cards.length === 0) return <p className="muted">No flashcards yet.</p>;

  const card = cards[index];
  const go = (delta: number) => {
    setIndex((i) => (i + delta + cards.length) % cards.length);
    setFlipped(false);
  };

  return (
    <div className="deck">
      <button
        type="button"
        className={`flashcard ${flipped ? "flipped" : ""}`}
        onClick={() => setFlipped((f) => !f)}
        aria-label="Flip card"
      >
        {weak.has(card.concept_id) && <span className="badge warn">Weak spot</span>}
        <span className="flashcard-side">{flipped ? "Answer" : "Question"}</span>
        <span className="flashcard-text">{flipped ? card.back : card.front}</span>
        {flipped && <span className="muted">Slide p. {card.page}</span>}
        {!flipped && <span className="muted">Click to flip</span>}
      </button>
      <div className="deck-nav">
        <button type="button" className="btn" onClick={() => go(-1)}>
          ← Prev
        </button>
        <span className="muted">
          {index + 1} / {cards.length}
        </span>
        <button type="button" className="btn" onClick={() => go(1)}>
          Next →
        </button>
      </div>
    </div>
  );
}
