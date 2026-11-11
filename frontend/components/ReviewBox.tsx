"use client";

// The drop target on the review page: concepts dragged (or clicked) in, then "Submit selection".

import { useState, type DragEvent } from "react";
import { DRAG_TYPE } from "./ConceptBlocks";

interface Props {
  selected: string[]; // concept ids, in the order the student added them
  nameOf: (id: string) => string;
  onAdd: (id: string) => void;
  onRemove: (id: string) => void;
  onSubmit: () => void;
  onReset: () => void;
  submitted: boolean;
  submitting: boolean;
}

export default function ReviewBox({ selected, nameOf, onAdd, onRemove, onSubmit, onReset, submitted, submitting }: Props) {
  const [over, setOver] = useState(false);

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setOver(false);
    if (submitted) return;
    const id = e.dataTransfer.getData(DRAG_TYPE) || e.dataTransfer.getData("text/plain");
    if (id) onAdd(id);
  }

  return (
    <section className="card" aria-label="Review box">
      <div className="card-head">
        <h3>Review box</h3>
        <span className="muted">{selected.length === 0 ? "nothing selected" : `${selected.length} selected`}</span>
      </div>

      <div
        className={`dropbox ${over ? "over" : ""} ${selected.length ? "filled" : ""}`}
        onDragOver={(e) => {
          if (submitted) return;
          e.preventDefault();
          e.dataTransfer.dropEffect = "copy";
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={onDrop}
      >
        {selected.length === 0 ? (
          <div className="dropbox-empty">
            <div className="dropbox-plus">+</div>
            <strong>Drop concepts here</strong>
            <span className="muted">One concept for a focused drill, several for a mixed review.</span>
          </div>
        ) : (
          selected.map((id) => (
            <span key={id} className="tag">
              {nameOf(id)}
              {!submitted && (
                <button type="button" className="tag-x" aria-label={`Remove ${nameOf(id)}`} onClick={() => onRemove(id)}>
                  ×
                </button>
              )}
            </span>
          ))
        )}
      </div>

      {submitted ? (
        <button type="button" className="btn wide" onClick={onReset}>
          Change selection
        </button>
      ) : (
        <button type="button" className="btn primary wide" disabled={selected.length === 0 || submitting} onClick={onSubmit}>
          {submitting ? "Preparing your review…" : "Submit selection"}
        </button>
      )}
    </section>
  );
}
