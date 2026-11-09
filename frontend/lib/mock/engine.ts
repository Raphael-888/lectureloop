// A small in-browser imitation of the backend agent, so every page works
// before the real API exists. It follows docs/api-contract.md exactly.
//
// Loop it imitates:
//   wrong answer on X  -> test an unmastered prerequisite of X (trace root cause)
//   no such prerequisite -> X is the root cause: explain with a slide citation, re-test X
//   correct but X still below threshold -> one more question on X
//   X mastered -> go back to the concept that was waiting on X, or cover the next concept
//
// BKT values are placeholders; the real model is D's backend/app/learner/bkt.py.

import type {
  AnswerResponse,
  Citation,
  ConceptsResponse,
  Mastery,
  MasteryLabel,
  NextAction,
  NotesResponse,
  Question,
  SessionResponse,
  TraceEvent,
  TraceResponse,
  UploadResponse,
} from "../types";
import {
  EXPLANATIONS,
  MOCK_CONCEPTS,
  MOCK_LECTURE_TITLE,
  MOCK_PAGE_COUNT,
  QUESTION_BANK,
  type BankItem,
} from "./data";

const MASTERED = 0.8;
const CONFUSED = 0.5;
const PRIOR = 0.5;
const LEARN = 0.1;
const SLIP = 0.1;
const GUESS: Record<BankItem["type"], number> = { multiple_choice: 0.25, short_answer: 0.05 };
const MAX_ATTEMPTS = 4; // stop re-testing one concept after this many answers
const PROCESSING_MS = 3000; // fake "parsing the PDF" time

const byId = new Map(MOCK_CONCEPTS.map((c) => [c.id, c]));

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function nameOf(id: string) {
  return byId.get(id)?.name ?? id;
}

// ---------- BKT (placeholder) ----------

function bktUpdate(p: number, correct: boolean, guess: number): number {
  const posterior = correct
    ? (p * (1 - SLIP)) / (p * (1 - SLIP) + (1 - p) * guess)
    : (p * SLIP) / (p * SLIP + (1 - p) * (1 - guess));
  return posterior + (1 - posterior) * LEARN;
}

function labelFor(p: number, tested: boolean): MasteryLabel {
  if (!tested) return "untested";
  if (p >= MASTERED) return "mastered";
  if (p >= CONFUSED) return "confused";
  return "not_mastered";
}

// ---------- coverage order: most advanced concepts first ----------

const depthMemo = new Map<string, number>();
function depth(id: string): number {
  const cached = depthMemo.get(id);
  if (cached !== undefined) return cached;
  depthMemo.set(id, 0); // guards against cycles
  const pre = byId.get(id)?.prerequisites ?? [];
  const d = pre.length ? 1 + Math.max(...pre.map(depth)) : 0;
  depthMemo.set(id, d);
  return d;
}
const COVERAGE_ORDER = [...MOCK_CONCEPTS].sort((a, b) => depth(b.id) - depth(a.id));

// ---------- state ----------

interface Issued {
  question: Question;
  item: BankItem;
}

interface SessionState {
  id: string;
  lectureId: string;
  p: Record<string, number>;
  attempts: Record<string, number>;
  tested: Set<string>;
  everWrong: Set<string>;
  issued: Map<string, Issued>;
  issueCount: Record<string, number>;
  stack: string[]; // concepts waiting while we check one of their prerequisites
  trace: TraceEvent[];
}

const lectures = new Map<string, number>(); // lecture id -> upload time
const sessions = new Map<string, SessionState>();
let sessionCounter = 0;

function addTrace(s: SessionState, tool: string, reason: string, summary: string) {
  s.trace.push({ step: s.trace.length + 1, time: new Date().toISOString(), tool, reason, summary });
}

function issue(s: SessionState, conceptId: string): Question {
  const bank = QUESTION_BANK[conceptId];
  const n = s.issueCount[conceptId] ?? 0;
  s.issueCount[conceptId] = n + 1;
  const item = bank[n % bank.length];
  const question: Question = {
    id: `${conceptId}__q${n + 1}`,
    concept_id: conceptId,
    type: item.type,
    prompt: item.prompt,
    ...(item.options ? { options: item.options } : {}),
  };
  s.issued.set(question.id, { question, item });
  return question;
}

function grade(item: BankItem, answer: string): boolean {
  if (item.type === "multiple_choice") {
    return answer.trim().toUpperCase() === (item.answer ?? "").toUpperCase();
  }
  const text = answer.toLowerCase();
  return (item.keywords ?? []).every((group) => group.some((k) => text.includes(k)));
}

function masteryList(s: SessionState): Mastery[] {
  return MOCK_CONCEPTS.map((c) => ({
    concept_id: c.id,
    p_mastery: Math.round(s.p[c.id] * 100) / 100,
    label: labelFor(s.p[c.id], s.tested.has(c.id)),
  }));
}

const pct = (p: number) => `${Math.round(p * 100)}%`;

// After a concept is mastered (or given up on): resume a waiting concept, or keep covering.
function advance(s: SessionState): { action: NextAction; questions: Question[] } {
  while (s.stack.length) {
    const parent = s.stack.pop()!;
    if (s.p[parent] >= MASTERED || (s.attempts[parent] ?? 0) >= MAX_ATTEMPTS) continue;
    addTrace(
      s,
      "generate_quiz",
      `Prerequisite fixed; returning to ${nameOf(parent)}`,
      `Generated 1 question on ${nameOf(parent)}`,
    );
    return { action: "next_question", questions: [issue(s, parent)] };
  }
  const remaining = COVERAGE_ORDER.filter((c) => !s.tested.has(c.id));
  if (remaining.length) {
    const next = remaining[0];
    addTrace(
      s,
      "generate_quiz",
      `Coverage: ${next.name} not tested yet (${remaining.length} concepts left)`,
      `Generated 1 question on ${next.name}`,
    );
    return { action: "next_question", questions: [issue(s, next.id)] };
  }
  addTrace(
    s,
    "export_flashcards",
    "Every concept is covered; build review material focused on weak spots",
    `Generated notes and ${MOCK_CONCEPTS.length} flashcards (${s.everWrong.size} weak concepts)`,
  );
  return { action: "done", questions: [] };
}

// ---------- public functions (same shapes as lib/api.ts) ----------

export async function uploadLecture(_file: File | null): Promise<UploadResponse> {
  await sleep(600);
  const lectureId = "l_demo";
  lectures.set(lectureId, Date.now());
  return { lecture_id: lectureId, status: "processing" };
}

export async function getConcepts(lectureId: string): Promise<ConceptsResponse> {
  await sleep(250);
  const uploadedAt = lectures.get(lectureId);
  const ready = uploadedAt === undefined || Date.now() - uploadedAt > PROCESSING_MS;
  return ready
    ? { lecture_id: lectureId, status: "ready", concepts: MOCK_CONCEPTS }
    : { lecture_id: lectureId, status: "processing", concepts: [] };
}

export async function startSession(lectureId: string): Promise<SessionResponse> {
  await sleep(500);
  sessionCounter += 1;
  const s: SessionState = {
    id: `s_mock_${sessionCounter}`,
    lectureId,
    p: Object.fromEntries(MOCK_CONCEPTS.map((c) => [c.id, PRIOR])),
    attempts: {},
    tested: new Set(),
    everWrong: new Set(),
    issued: new Map(),
    issueCount: {},
    stack: [],
    trace: [],
  };
  sessions.set(s.id, s);

  const links = MOCK_CONCEPTS.reduce((n, c) => n + c.prerequisites.length, 0);
  addTrace(
    s,
    "extract_concepts",
    `Read ${MOCK_LECTURE_TITLE} before quizzing`,
    `Found ${MOCK_CONCEPTS.length} concepts and ${links} prerequisite links across ${MOCK_PAGE_COUNT} pages`,
  );
  const first = COVERAGE_ORDER[0];
  addTrace(
    s,
    "generate_quiz",
    "Coverage pass: start with the most advanced concept so gaps can be traced back",
    `Generated 1 question on ${first.name}`,
  );
  return { session_id: s.id, questions: [issue(s, first.id)] };
}

export async function submitAnswer(
  sessionId: string,
  questionId: string,
  answer: string,
): Promise<AnswerResponse> {
  await sleep(700);
  const s = sessions.get(sessionId);
  if (!s) throw new Error("Session not found (mock data resets when the page reloads). Start again from the upload page.");
  const issued = s.issued.get(questionId);
  if (!issued) throw new Error(`Unknown question ${questionId}`);

  const cid = issued.question.concept_id;
  const concept = byId.get(cid)!;
  const correct = grade(issued.item, answer);
  const before = s.p[cid];
  const after = bktUpdate(before, correct, GUESS[issued.item.type]);
  s.p[cid] = after;
  s.tested.add(cid);
  s.attempts[cid] = (s.attempts[cid] ?? 0) + 1;
  if (!correct) s.everWrong.add(cid);

  addTrace(
    s,
    "grade_answer",
    `Grade the answer to "${concept.name}"`,
    correct ? "Correct" : `Incorrect (answered: ${answer.trim().slice(0, 40) || "blank"})`,
  );
  addTrace(
    s,
    "update_mastery",
    "Update BKT mastery for the tested concept",
    `${concept.name}: ${pct(before)} → ${pct(after)}`,
  );

  let feedback = "";
  let citation: Citation | null = null;
  let action: NextAction = "next_question";
  let next: Question[] = [];

  // X is the root cause: re-explain with a slide citation, then re-test X.
  const explainRoot = (rootId: string, preface: string) => {
    const root = byId.get(rootId)!;
    const exp = EXPLANATIONS[rootId];
    feedback = `${preface}${exp.text}`;
    citation = { page: exp.page, quote: exp.quote };
    addTrace(
      s,
      "trace_root_cause",
      root.prerequisites.length
        ? `All prerequisites of ${root.name} check out`
        : `${root.name} has no prerequisites in this lecture`,
      `Root cause found: ${root.name}`,
    );
    addTrace(
      s,
      "search_slides",
      `Find slide evidence to re-explain ${root.name}`,
      `Cited page ${exp.page} (concept appears on pages ${root.pages.join(", ")})`,
    );
    if ((s.attempts[rootId] ?? 0) < MAX_ATTEMPTS) {
      action = "explain";
      addTrace(
        s,
        "generate_quiz",
        `Re-test ${root.name} with a new question after the explanation`,
        `Generated 1 question on ${root.name}`,
      );
      next = [issue(s, rootId)];
    } else {
      const r = advance(s);
      action = r.action === "done" ? "done" : "explain";
      next = r.questions;
    }
  };

  const uncheckedPrereq = (id: string) =>
    byId.get(id)!.prerequisites.find((pid) => s.p[pid] < MASTERED && !s.stack.includes(pid) && pid !== cid);

  if (!correct) {
    const prereq = uncheckedPrereq(cid);
    if (prereq && s.attempts[cid] < MAX_ATTEMPTS) {
      s.stack.push(cid);
      action = "test_prerequisite";
      feedback = `Not quite. Before re-explaining ${concept.name}, let's check whether a prerequisite is the real gap.`;
      addTrace(
        s,
        "trace_root_cause",
        `${concept.name} below threshold; testing prerequisite ${nameOf(prereq)}`,
        `Generated 1 question on ${nameOf(prereq)}`,
      );
      next = [issue(s, prereq)];
    } else {
      explainRoot(cid, "");
    }
  } else if (after < MASTERED && s.attempts[cid] < MAX_ATTEMPTS) {
    feedback = `Correct. ${concept.summary ?? ""}`.trim();
    action = "next_question";
    addTrace(
      s,
      "generate_quiz",
      `${concept.name} at ${pct(after)}, below the ${pct(MASTERED)} mastery threshold; confirm with one more question`,
      `Generated 1 question on ${concept.name}`,
    );
    next = [issue(s, cid)];
  } else if (s.stack.length && !s.everWrong.has(cid)) {
    // This prerequisite was never a problem, so it is not the gap.
    const parent = s.stack[s.stack.length - 1];
    const other = uncheckedPrereq(parent);
    if (other) {
      feedback = `Correct, so ${concept.name} is not the gap. Let's check another prerequisite of ${nameOf(parent)}.`;
      action = "test_prerequisite";
      addTrace(
        s,
        "trace_root_cause",
        `${concept.name} is mastered; testing next prerequisite of ${nameOf(parent)}: ${nameOf(other)}`,
        `Generated 1 question on ${nameOf(other)}`,
      );
      next = [issue(s, other)];
    } else {
      s.stack.pop();
      explainRoot(parent, `Correct, so the prerequisites are fine. The gap is ${nameOf(parent)} itself. `);
    }
  } else {
    // mastered (or out of attempts): resume a waiting concept or keep covering
    feedback = `Correct. ${concept.summary ?? ""}`.trim();
    const r = advance(s);
    action = r.action;
    next = r.questions;
  }

  return {
    correct,
    concept_id: cid,
    feedback,
    citation,
    mastery: masteryList(s),
    next_action: action,
    next_questions: next,
  };
}

export async function getTrace(sessionId: string, afterStep: number): Promise<TraceResponse> {
  await sleep(150);
  const s = sessions.get(sessionId);
  return { events: s ? s.trace.filter((e) => e.step > afterStep) : [] };
}

export async function getNotes(sessionId: string): Promise<NotesResponse> {
  await sleep(500);
  const weak = new Set(sessions.get(sessionId)?.everWrong ?? []);

  const lines = [`# ${MOCK_LECTURE_TITLE}`, "", "## Key concepts", ""];
  for (const c of MOCK_CONCEPTS) {
    lines.push(`### ${c.name} (p. ${c.pages.join(", ")})`);
    if (weak.has(c.id)) lines.push("", "> ⚠️ **You struggled with this one. Review it first.**");
    lines.push("", c.summary ?? "", "");
  }

  const cards = MOCK_CONCEPTS.map((c) => ({
    front: `${c.name}: what is it?`,
    back: c.summary ?? "",
    concept_id: c.id,
    page: c.pages[0],
  })).sort((a, b) => Number(weak.has(b.concept_id)) - Number(weak.has(a.concept_id)));

  return { summary_markdown: lines.join("\n"), weak_concepts: [...weak], flashcards: cards };
}

export async function getFlashcardsCsv(sessionId: string): Promise<string> {
  const notes = await getNotes(sessionId);
  const esc = (v: string) => `"${v.replace(/"/g, '""')}"`;
  return notes.flashcards.map((f) => `${esc(f.front)},${esc(`${f.back} (slide p. ${f.page})`)}`).join("\n");
}
