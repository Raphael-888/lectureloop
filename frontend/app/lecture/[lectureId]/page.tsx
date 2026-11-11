"use client";

// Page 2: lecture overview — a summary and the concepts as a tree, in lecture order.

import Link from "next/link";
import { useParams } from "next/navigation";
import ConceptBlocks from "@/components/ConceptBlocks";
import Markdown from "@/components/Markdown";
import StepBar from "@/components/StepBar";
import { useLecture } from "@/lib/useLecture";

export default function OverviewPage() {
  const { lectureId } = useParams<{ lectureId: string }>();
  const { lecture, concepts, blocks, error } = useLecture(lectureId);

  if (error) return <p className="error narrow">{error}</p>;
  if (!lecture) {
    return (
      <p className="status narrow">
        <span className="spinner" /> Reading the slides and mapping concepts…
      </p>
    );
  }

  const links = concepts.reduce((n, c) => n + c.prerequisites.length, 0);
  const reviewHref = `/lecture/${encodeURIComponent(lectureId)}/review`;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow">Lecture parsed</div>
          <h1>{lecture.title || "Your lecture"}</h1>
        </div>
        <StepBar current={2} />
      </div>

      <div className="stats">
        <div className="stat">
          <div className="stat-n">{blocks.length}</div>
          <div className="muted">topics, in the order the lecture taught them</div>
        </div>
        <div className="stat">
          <div className="stat-n">{concepts.length}</div>
          <div className="muted">concepts you can review one at a time or together</div>
        </div>
        <div className="stat">
          <div className="stat-n">{lecture.page_count ?? "–"}</div>
          <div className="muted">slides · {links} prerequisite links between concepts</div>
        </div>
      </div>

      {lecture.overview && (
        <section className="card">
          <div className="eyebrow">Summary</div>
          <Markdown>{lecture.overview}</Markdown>
        </section>
      )}

      <section className="card">
        <div className="card-head">
          <h3>What the lecture covers</h3>
          <span className="muted">Each concept is linked to its slides</span>
        </div>
        <ConceptBlocks blocks={blocks} variant="detail" />
      </section>

      <div className="cta-row">
        <span className="muted">Already know most of this? Skip straight to the parts you&apos;re unsure about.</span>
        <Link className="btn primary" href={reviewHref}>
          Pick what to review →
        </Link>
      </div>
    </div>
  );
}
