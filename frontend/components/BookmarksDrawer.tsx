"use client";

// The star button's panel: questions the student saved during quizzes (the "mistake book").

import type { BookmarkItem } from "@/lib/types";

interface Props {
  open: boolean;
  items: BookmarkItem[];
  onClose: () => void;
  onReview: (conceptId: string) => void; // start a session on that concept (starred question first)
  onRemove: (item: BookmarkItem) => void;
}

export default function BookmarksDrawer({ open, items, onClose, onReview, onRemove }: Props) {
  if (!open) return null;
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" onClick={(e) => e.stopPropagation()} aria-label="Saved questions">
        <div className="card-head">
          <h3>★ Saved questions</h3>
          <button type="button" className="btn tiny" onClick={onClose}>
            Close
          </button>
        </div>
        {items.length === 0 ? (
          <div className="drawer-empty">
            <div className="dropbox-plus">★</div>
            <strong>Nothing saved yet</strong>
            <span className="muted">Star a question during a quiz and it will show up here. Starred questions come first next time you review that concept.</span>
          </div>
        ) : (
          <ul className="bookmark-list">
            {items.map((b) => (
              <li key={b.question.id} className="bookmark">
                <div className="bookmark-top">
                  <span className="pill">{b.concept_name}</span>
                  {b.correct === false && <span className="pill warn">got it wrong</span>}
                  {b.correct === true && <span className="pill ok">got it right</span>}
                </div>
                <div className="bookmark-prompt">{b.question.prompt}</div>
                {b.your_answer && <div className="muted">Your answer: {b.your_answer}</div>}
                <div className="row">
                  <button type="button" className="btn tiny" onClick={() => onReview(b.question.concept_id)}>
                    Practice this concept
                  </button>
                  <button type="button" className="btn tiny" onClick={() => onRemove(b)}>
                    Remove
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </aside>
    </div>
  );
}
