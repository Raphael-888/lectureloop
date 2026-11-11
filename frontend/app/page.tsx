"use client";

// Page 1: upload slides, wait for processing, then start the review.

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import * as api from "@/lib/api";
import { MAX_UPLOAD_MB, USE_MOCK } from "@/lib/config";
import type { Concept } from "@/lib/types";

type Phase = "idle" | "uploading" | "processing" | "ready" | "error";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [lectureId, setLectureId] = useState<string | null>(null);
  const [concepts, setConcepts] = useState<Concept[]>([]);
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
      setLectureId(res.lecture_id);
      setPhase("processing");
      // poll until the backend has extracted the concepts (up to ~3 minutes)
      for (let i = 0; i < 120 && alive.current; i++) {
        const c = await api.getConcepts(res.lecture_id);
        if (c.status === "ready") {
          setConcepts(c.concepts);
          setPhase("ready");
          return;
        }
        if (c.status === "failed") throw new Error("The lecture could not be processed. Try another PDF.");
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
      <h1>Did you really get today&apos;s lecture?</h1>
      <p className="lead">
        Upload the slides. LectureLoop quizzes you on every concept, traces each mistake back to
        the prerequisite you&apos;re actually missing, and keeps teaching until you&apos;ve got it.
      </p>

      {phase !== "ready" && (
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
            <input
              type="file"
              accept="application/pdf,.pdf"
              hidden
              disabled={busy}
              onChange={(e) => pick(e.target.files?.[0])}
            />
            <span className="dropzone-icon">📄</span>
            <strong>{file ? file.name : "Drop lecture slides here or click to choose"}</strong>
            <span className="muted">
              {file ? `${(file.size / 1024 / 1024).toFixed(1)} MB` : `PDF only, up to ${MAX_UPLOAD_MB} MB`}
            </span>
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
              {phase === "uploading"
                ? "Uploading…"
                : "Reading the slides and mapping concepts and prerequisites…"}
            </p>
          )}
          {error && <p className="error">{error}</p>}
        </section>
      )}

      {phase === "ready" && lectureId && (
        <section className="card">
          <h2>Found {concepts.length} concepts</h2>
          <p className="muted">Every one of them will be covered in your review.</p>
          <ul className="chips">
            {concepts.map((c) => (
              <li key={c.id}>
                {c.name} <span className="muted">p. {c.pages.join(", ")}</span>
              </li>
            ))}
          </ul>
          <Link className="btn primary" href={`/lecture/${encodeURIComponent(lectureId)}/study`}>
            Start review →
          </Link>
        </section>
      )}
    </div>
  );
}
