"use client";

// Page 1: upload slides, wait for processing, then go to the lecture overview.

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import * as api from "@/lib/api";
import { MAX_UPLOAD_MB, USE_MOCK } from "@/lib/config";

type Phase = "idle" | "uploading" | "processing" | "error";

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  function pick(f: File | undefined) {
    setError(null);
    if (!f) return;
    const isPdf = f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) return setError("Only PDF files are supported.");
    if (f.size > MAX_UPLOAD_MB * 1024 * 1024) return setError(`The file is larger than ${MAX_UPLOAD_MB} MB.`);
    setFile(f);
  }

  async function start(f: File | null) {
    setError(null);
    setPhase("uploading");
    try {
      const res = await api.uploadLecture(f);
      setPhase("processing");
      // poll until the backend has extracted the concepts (up to ~4 minutes with a real model)
      for (let i = 0; i < 160 && alive.current; i++) {
        const c = await api.getConcepts(res.lecture_id);
        if (c.status === "ready") {
          router.push(`/lecture/${encodeURIComponent(res.lecture_id)}`);
          return;
        }
        if (c.status === "failed") throw new Error(c.error || "The lecture could not be processed. Try another PDF.");
        await new Promise((r) => setTimeout(r, 1500));
      }
      if (alive.current) throw new Error("Processing is taking too long. Please try again.");
    } catch (e) {
      if (!alive.current) return;
      setError(api.errorMessage(e));
      setPhase("error");
    }
  }

  const busy = phase === "uploading" || phase === "processing";

  return (
    <div className="narrow">
      <div className="eyebrow">After the lecture</div>
      <h1>Which parts didn&apos;t stick?</h1>
      <p className="lead">
        Upload the slides. LectureLoop maps the lecture into concepts, lets you pick the ones you&apos;re unsure
        about, and quizzes you on exactly those, tracing every mistake back to the idea you&apos;re actually missing.
      </p>

      <section className="card">
        <label
          className={`dropzone ${dragging ? "dragging" : ""} ${busy ? "disabled" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            if (!busy) pick(e.dataTransfer.files[0]);
          }}
        >
          <input type="file" accept="application/pdf,.pdf" hidden disabled={busy} onChange={(e) => pick(e.target.files?.[0])} />
          <span className="dropzone-icon">📄</span>
          <strong>{file ? file.name : "Drop lecture slides here or click to choose"}</strong>
          <span className="muted">{file ? `${(file.size / 1024 / 1024).toFixed(1)} MB` : `PDF only, up to ${MAX_UPLOAD_MB} MB`}</span>
        </label>

        <div className="row">
          <button className="btn primary" disabled={!file || busy} onClick={() => start(file)}>
            Upload and analyze
          </button>
          {USE_MOCK && (
            <button className="btn" disabled={busy} onClick={() => start(null)}>
              Try the demo lecture
            </button>
          )}
        </div>

        {busy && (
          <p className="status">
            <span className="spinner" />
            {phase === "uploading" ? "Uploading…" : "Reading the slides and mapping concepts and prerequisites… this takes a moment."}
          </p>
        )}
        {error && <p className="error">{error}</p>}
      </section>

      <div className="hint-stickies">
        <div className="sticky-note s-yellow">
          <b>1 · Concepts</b>
          <span>the lecture bursts into its concepts, coloured by what you know</span>
        </div>
        <div className="sticky-note s-pink">
          <b>2 · Pick</b>
          <span>click the ones you&apos;re unsure about and confirm</span>
        </div>
        <div className="sticky-note s-green">
          <b>3 · Quiz</b>
          <span>the tutor tests you, finds the root cause of each mistake and re-teaches it</span>
        </div>
      </div>
    </div>
  );
}
