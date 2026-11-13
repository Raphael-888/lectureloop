"use client";

// The tutor as a small floating button on the quiz page; expands into the chat panel.

import { useState } from "react";
import TutorChat from "./TutorChat";
import type { ChatMessage } from "@/lib/types";

interface Props {
  messages: ChatMessage[];
  onSend: (message: string) => Promise<void>;
}

export default function FloatingChat({ messages, onSend }: Props) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`floating ${open ? "open" : ""}`}>
      {open ? (
        <div className="floating-panel">
          <button type="button" className="floating-close" aria-label="Minimise the tutor" onClick={() => setOpen(false)}>
            ─
          </button>
          <TutorChat
            compact
            title="Tutor"
            intro="Stuck? Ask me about this question, or tell me to make the quiz easier, harder, or a different type."
            messages={messages}
            onSend={onSend}
            suggestions={["Give me a hint", "Explain this slide again", "Make it easier"]}
          />
        </div>
      ) : (
        <button type="button" className="floating-btn" onClick={() => setOpen(true)}>
          ↻ Ask the tutor{messages.length ? ` (${messages.length})` : ""}
        </button>
      )}
    </div>
  );
}
