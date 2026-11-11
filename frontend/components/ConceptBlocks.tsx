"use client";

// The lecture as a vertical spine of topic blocks, concepts branching to the right.
// variant "detail": overview page (name + summary cards)
// variant "pick":   review page (draggable chips; click also toggles)

import type { DragEvent } from "react";
import type { ConceptBlock } from "@/lib/groups";
import type { MasteryLabel } from "@/lib/types";

export const DRAG_TYPE = "application/x-lectureloop-concept";

interface Props {
  blocks: ConceptBlock[];
  variant: "detail" | "pick";
  selected?: Set<string>;
  onToggle?: (conceptId: string) => void;
  disabled?: boolean;
  mastery?: Record<string, MasteryLabel>; // optional colouring (quiz results)
}

export default function ConceptBlocks({ blocks, variant, selected, onToggle, disabled, mastery }: Props) {
  function startDrag(e: DragEvent<HTMLButtonElement>, id: string) {
    e.dataTransfer.setData(DRAG_TYPE, id);
    e.dataTransfer.setData("text/plain", id);
    e.dataTransfer.effectAllowed = "copy";
  }

  return (
    <div className="blocks">
      {blocks.map((block, i) => (
        <div key={block.n} className="block">
          <div className="block-spine">
            <div className="block-num">{block.n}</div>
            {i < blocks.length - 1 && <div className="block-line" />}
          </div>
          <div className="block-body">
            <div className="block-head">
              <div className="block-title">{block.title}</div>
              <span className="pill">p. {block.pages}</span>
            </div>

            {variant === "detail" ? (
              <div className="concept-cards">
                {block.concepts.map((c) => (
                  <div key={c.id} className="concept-card">
                    <span className="dot" />
                    <div>
                      <div className="concept-card-name">
                        {c.name} <span className="muted">p.{c.pages.join(", ")}</span>
                      </div>
                      {c.summary && <div className="concept-card-summary">{c.summary}</div>}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="chips-branch">
                {block.concepts.map((c) => {
                  const on = selected?.has(c.id) ?? false;
                  const label = mastery?.[c.id];
                  return (
                    <button
                      key={c.id}
                      type="button"
                      className={`chip ${on ? "on" : ""} ${label ? `m-${label}` : ""}`}
                      draggable={!disabled}
                      disabled={disabled}
                      aria-pressed={on}
                      onDragStart={(e) => startDrag(e, c.id)}
                      onClick={() => onToggle?.(c.id)}
                      title={c.summary}
                    >
                      <svg aria-hidden="true" width="10" height="14" viewBox="0 0 12 16" fill="currentColor" opacity="0.45">
                        <circle cx="3" cy="3" r="1.5" /><circle cx="9" cy="3" r="1.5" />
                        <circle cx="3" cy="8" r="1.5" /><circle cx="9" cy="8" r="1.5" />
                        <circle cx="3" cy="13" r="1.5" /><circle cx="9" cy="13" r="1.5" />
                      </svg>
                      <span>{c.name}</span>
                      <span className="chip-page">p.{c.pages[0]}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
