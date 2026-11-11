// A small in-browser imitation of the backend agent, so every page works
// before the real API exists. It follows docs/api-contract.md exactly.
//
// Loop it imitates (scoped to the concepts the student selected):
//   wrong answer on X  -> test an unmastered prerequisite of X (trace root cause), even outside the scope
//   no such prerequisite -> X is the root cause: explain with a slide citation, re-test X
//   correct but X still below threshold -> one more question on X
//   X mastered -> go back to the concept that was waiting on X, or cover the next selected concept
//
// BKT values are placeholders; the real model is D's backend/app/learner/bkt.py.

import type {
  AnswerResponse,
  ChatMessage,
  ChatResponse,
  Citation,
  ConceptsResponse,
  Mastery,
  MasteryLabel,
  NextAction,
  NotesResponse,
  PagesResponse,
  Preferences,
  Question,
  QuestionType,
  SessionResponse,
  SessionState,
  TraceEvent,
  TraceResponse,
  UploadResponse,
} from "../types";
import {
  EXPLANATIONS,
  MOCK_CONCEPTS,
  MOCK_LECTURE_TITLE,
  MOCK_PAGE_COUNT,
  MOCK_PAGES,
  QUESTION_BANK,
  type BankItem,
} from "./data";

const MASTERED = 0.8;
const CONFUSED = 0.5;
const PRIOR = 0.3;
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

interface SessionData {
  id: string;
  lectureId: string;
  targets: string[]; // selected concept ids (empty = whole lecture)
  summary: string;
  preferences: Preferences;
  chat: ChatMessage[];
  p: Record<string, number>;
  attempts: Record<string, number>;
  tested: Set<string>;
  everWrong: Set<string>;
  issued: Map<string, Issued>;
  issueCount: Record<string, number>;
  current: Question | null;
  answered: number;
  stack: string[]; // concepts waiting while we check one of their prerequisites
  trace: TraceEvent[];
  done: boolean;
}

const lectures = new Map<string, number>(); // lecture id -> upload time
const sessions = new Map<string, SessionData>();
let sessionCounter = 0;

function addTrace(s: SessionData, tool: string, reason: string, summary: string) {
  s.trace.push({ step: s.trace.length + 1, time: new Date().toISOString(), tool, reason, summary });
}

function scopeOf(s: SessionData) {
  return s.targets.length ? COVERAGE_ORDER.filter((c) => s.targets.includes(c.id)) : COVERAGE_ORDER;
}

function inScope(s: SessionData, id: string) {
  return s.targets.length === 0 || s.targets.includes(id);
}

function issue(s: SessionData, conceptId: string): Question {
  const bank = QUESTION_BANK[conceptId];
  const n = s.issueCount[conceptId] ?? 0;
  s.issueCount[conceptId] = n + 1;
  // the student's preference (set in the chat) wins; otherwise multiple choice first
  const wanted: QuestionType | null = s.preferences.question_type;
  let ordered = wanted ? bank.filter((b) => b.type === wanted) : bank;
  if (ordered.length === 0) {
    // the demo bank has no question of that type: make one from the concept summary,
    // the way the real backend generates on demand
    const c = byId.get(conceptId)!;
    const keywords = (c.summary ?? "")
      .toLowerCase()
      .match(/[a-z]{5,}/g)
      ?.slice(0, 3)
      .map((w) => [w]) ?? [];
    ordered =
      wanted === "short_answer"
        ? [{ type: "short_answer", prompt: `In your own words, explain this idea from the lecture: ${c.name}.`, keywords }]
        : bank;
  }
  const item = ordered[n % ordered.length];
  const harder = s.preferences.difficulty === "harder" ? " (apply it, don't just recall it)" : "";
  const question: Question = {
    id: `${conceptId}__q${n + 1}`,
    concept_id: conceptId,
    type: item.type,
    prompt: item.prompt + (item.type === "short_answer" ? harder : ""),
    ...(item.options ? { options: item.options } : {}),
  };
  s.issued.set(question.id, { question, item });
  s.current = question;
  return question;
}

function grade(item: BankItem, answer: string): boolean {
  if (item.type === "multiple_choice") {
    return answer.trim().toUpperCase() === (item.answer ?? "").toUpperCase();
  }
  const text = answer.toLowerCase();
  return (item.keywords ?? []).every((group) => group.some((k) => text.includes(k)));
}

function masteryList(s: SessionData): Mastery[] {
  return MOCK_CONCEPTS.map((c) => ({
    concept_id: c.id,
    p_mastery: Math.round((s.p[c.id] ?? PRIOR) * 100) / 100,
    label: labelFor(s.p[c.id] ?? PRIOR, s.tested.has(c.id)),
  }));
}

const pct = (p: number) => `${Math.round(p * 100)}%`;

function summaryFor(ids: string[]): string {
  const cs = ids.map((id) => byId.get(id)!).filter(Boolean);
  const names = cs.map((c) => c.name);
  const intro =
    cs.length === 1
      ? `You are reviewing one concept: ${names[0]}.`
      : `You are reviewing ${cs.length} concepts: ${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}.`;
  return [intro, "", ...cs.map((c) => `- **${c.name}** (p. ${c.pages.join(", ")}): ${c.summary}`)].join("\n");
}

// After a concept is mastered (or given up on): resume a waiting concept, or keep covering.
function advance(s: SessionData): { action: NextAction; questions: Question[] } {
  while (s.stack.length) {
    const parent = s.stack.pop()!;
    if ((s.p[parent] ?? PRIOR) >= MASTERED || (s.attempts[parent] ?? 0) >= MAX_ATTEMPTS) continue;
    addTrace(s, "generate_quiz", `Prerequisite fixed; returning to ${nameOf(parent)}`, `1 question on ${nameOf(parent)}`);
    return { action: "next_question", questions: [issue(s, parent)] };
  }
  const remaining = scopeOf(s).filter((c) => !s.tested.has(c.id));
  if (remaining.length) {
    const next = remaining[0];
    addTrace(
      s,
      "generate_quiz",
      `Coverage: ${next.name} not tested yet (${remaining.length} selected concepts left)`,
      `1 question on ${next.name}`,
    );
    return { action: "next_question", questions: [issue(s, next.id)] };
  }
  s.done = true;
  s.current = null;
  const reviewed = MOCK_CONCEPTS.filter((c) => inScope(s, c.id) || s.tested.has(c.id));
  const weak = reviewed.filter((c) => s.everWrong.has(c.id) || (s.tested.has(c.id) && s.p[c.id] < MASTERED));
  addTrace(
    s,
    "export_flashcards",
    "Every selected concept is mastered or out of attempts; build review material on the weak spots",
    `Notes and ${reviewed.length} flashcards ready (${weak.length} weak concepts)`,
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

const OVERVIEW = [
  "This lecture builds one idea in three steps. It defines what a loss is and why we minimize empirical risk, applies that to fitting a line with squared loss (by gradient descent or in closed form), then shows how the cost surface and the normal equation connect.",
  "",
  ...MOCK_CONCEPTS.map((c) => `- **${c.name}** (p. ${c.pages.join(", ")}): ${c.summary}`),
].join("\n");

export async function getConcepts(lectureId: string): Promise<ConceptsResponse> {
  await sleep(250);
  const uploadedAt = lectures.get(lectureId);
  const ready = uploadedAt === undefined || Date.now() - uploadedAt > PROCESSING_MS;
  return ready
    ? {
        lecture_id: lectureId,
        status: "ready",
        error: null,
        title: MOCK_LECTURE_TITLE,
        page_count: MOCK_PAGE_COUNT,
        overview: OVERVIEW,
        concepts: MOCK_CONCEPTS,
      }
    : { lecture_id: lectureId, status: "processing", error: null, concepts: [] };
}

export async function getPages(lectureId: string, conceptIds: string[] = []): Promise<PagesResponse> {
  await sleep(200);
  const wanted = new Set(conceptIds);
  const pages = MOCK_PAGES.map((p) => ({
    page: p.page,
    title: p.title,
    page_type: p.page <= 2 || p.page === MOCK_PAGE_COUNT ? "title" : "content",
    text: p.text,
    concept_ids: MOCK_CONCEPTS.filter((c) => c.pages.includes(p.page)).map((c) => c.id),
  })).filter((p) => wanted.size === 0 || p.concept_ids.some((id) => wanted.has(id)));
  return { lecture_id: lectureId, pages };
}

export async function startSession(lectureId: string, conceptIds: string[]): Promise<SessionResponse> {
  await sleep(900);
  const targets = conceptIds.filter((id, i) => byId.has(id) && conceptIds.indexOf(id) === i);
  sessionCounter += 1;
  const s: SessionData = {
    id: `s_mock_${sessionCounter}`,
    lectureId,
    targets,
    summary: summaryFor(targets.length ? targets : MOCK_CONCEPTS.map((c) => c.id)),
    preferences: { question_type: null, difficulty: "same" },
    chat: [],
    p: {},
    attempts: {},
    tested: new Set(),
    everWrong: new Set(),
    issued: new Map(),
    issueCount: {},
    current: null,
    answered: 0,
    stack: [],
    trace: [],
    done: false,
  };
  sessions.set(s.id, s);

  const links = MOCK_CONCEPTS.reduce((n, c) => n + c.prerequisites.length, 0);
  addTrace(
    s,
    "extract_concepts",
    `Read ${MOCK_LECTURE_TITLE} before quizzing`,
    `Found ${MOCK_CONCEPTS.length} concepts and ${links} prerequisite links on ${MOCK_PAGE_COUNT} pages`,
  );
  if (targets.length) {
    addTrace(
      s,
      "review_scope",
      "The student chose what to review; quiz only those concepts",
      `Scope: ${targets.map(nameOf).join(", ")} (${targets.length} of ${MOCK_CONCEPTS.length} concepts)`,
    );
  }
  addTrace(
    s,
    "summarize",
    "Summarise what is being reviewed before the first question",
    `Summary of ${targets.length || MOCK_CONCEPTS.length} concepts written from the slides`,
  );
  const first = scopeOf(s)[0];
  addTrace(
    s,
    "generate_quiz",
    "Coverage pass: start with the most advanced selected concept so gaps can be traced back",
    `1 question on ${first.name}`,
  );
  return { session_id: s.id, questions: [issue(s, first.id)] };
}

function sessionOr404(sessionId: string): SessionData {
  const s = sessions.get(sessionId);
  if (!s) throw new Error("Session not found (mock data resets when the page reloads). Start again from the upload page.");
  return s;
}

export async function getSession(sessionId: string): Promise<SessionState> {
  await sleep(200);
  const s = sessionOr404(sessionId);
  return {
    session_id: s.id,
    lecture_id: s.lectureId,
    concept_ids: s.targets.length ? s.targets : MOCK_CONCEPTS.map((c) => c.id),
    scope_summary: s.summary,
    preferences: s.preferences,
    chat: s.chat,
    current_question: s.current,
    mastery: masteryList(s),
    answered: s.answered,
    done: s.done,
  };
}

const HARDER = /\b(harder|more difficult|challeng|tough|advanced|calculation|apply|proof)/i;
const EASIER = /\b(easier|simpler|simple|basic|gentle|beginner|too hard)/i;
const MCQ = /\b(multiple[- ]choice|mcq|options|choices)/i;
const OPEN = /\b(short[- ]answer|open[- ]ended|free[- ]text|written|in my own words|essay)\b/i;

export async function chat(sessionId: string, message: string): Promise<ChatResponse> {
  await sleep(700);
  const s = sessionOr404(sessionId);
  const before = { ...s.preferences };
  if (MCQ.test(message)) s.preferences.question_type = "multiple_choice";
  else if (OPEN.test(message)) s.preferences.question_type = "short_answer";
  if (HARDER.test(message)) s.preferences.difficulty = "harder";
  else if (EASIER.test(message)) s.preferences.difficulty = "easier";
  const changed = (["question_type", "difficulty"] as const).filter((k) => s.preferences[k] !== before[k]);

  let reply: string;
  if (changed.length) {
    const parts: string[] = [];
    if (changed.includes("question_type")) {
      parts.push(
        s.preferences.question_type === "short_answer"
          ? "From the next question on you'll get open (short-answer) questions."
          : "From the next question on you'll get multiple-choice questions.",
      );
    }
    if (changed.includes("difficulty")) {
      parts.push(
        s.preferences.difficulty === "harder"
          ? "The next questions will be harder: applying the idea, not just recalling it."
          : "The next questions will be easier and more about recall.",
      );
    }
    reply = `Got it. ${parts.join(" ")}`;
  } else {
    // answer from the "slides": the selected concept whose summary shares the most words
    const words = new Set(message.toLowerCase().match(/[a-z0-9]+/g) ?? []);
    const scope = s.targets.length ? s.targets.map((id) => byId.get(id)!) : MOCK_CONCEPTS;
    const best = [...scope, ...MOCK_CONCEPTS]
      .map((c) => ({ c, hit: (`${c.name} ${c.summary}`.toLowerCase().match(/[a-z0-9]+/g) ?? []).filter((w) => words.has(w) && w.length > 3).length }))
      .sort((a, b) => b.hit - a.hit)[0];
    const c = best && best.hit > 0 ? best.c : scope[0];
    reply = `${EXPLANATIONS[c.id].text} (p. ${EXPLANATIONS[c.id].page})`;
  }
  s.chat.push({ role: "student", text: message, time: new Date().toISOString() });
  s.chat.push({ role: "tutor", text: reply, time: new Date().toISOString() });
  addTrace(
    s,
    "chat",
    `Student wrote: "${message.slice(0, 80)}"`,
    changed.length ? `Updated quiz settings: ${changed.map((k) => `${k}=${s.preferences[k]}`).join(", ")}` : "Answered from the slides",
  );
  return { reply, preferences: { ...s.preferences }, changed: [...changed] };
}

export async function submitAnswer(sessionId: string, questionId: string, answer: string): Promise<AnswerResponse> {
  await sleep(700);
  const s = sessionOr404(sessionId);
  const issued = s.issued.get(questionId);
  if (!issued) throw new Error(`Unknown question ${questionId}`);

  const cid = issued.question.concept_id;
  const concept = byId.get(cid)!;
  const correct = grade(issued.item, answer);
  const before = s.p[cid] ?? PRIOR;
  const after = bktUpdate(before, correct, GUESS[issued.item.type]);
  s.p[cid] = after;
  s.tested.add(cid);
  s.attempts[cid] = (s.attempts[cid] ?? 0) + 1;
  s.answered += 1;
  s.current = null;
  if (!correct) s.everWrong.add(cid);

  addTrace(
    s,
    "grade_answer",
    `Grade the answer to "${concept.name}"`,
    correct ? "Correct" : `Incorrect (answered: ${answer.trim().slice(0, 40) || "blank"})`,
  );
  addTrace(s, "update_mastery", "Update BKT mastery for the tested concept", `${concept.name}: ${pct(before)} → ${pct(after)}`);

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
      root.prerequisites.length ? `All prerequisites of ${root.name} check out` : `${root.name} has no prerequisites in this lecture`,
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
      addTrace(s, "generate_quiz", `Re-test ${root.name} with a new question after the explanation`, `1 question on ${root.name}`);
      next = [issue(s, rootId)];
    } else {
      const r = advance(s);
      action = r.action === "done" ? "done" : "explain";
      next = r.questions;
    }
  };

  const uncheckedPrereq = (id: string) =>
    byId.get(id)!.prerequisites.find((pid) => (s.p[pid] ?? PRIOR) < MASTERED && !s.stack.includes(pid) && pid !== cid);

  if (!correct) {
    const prereq = uncheckedPrereq(cid);
    if (prereq && s.attempts[cid] < MAX_ATTEMPTS) {
      s.stack.push(cid);
      action = "test_prerequisite";
      feedback = `Not quite. Before re-explaining ${concept.name}, let's check whether a prerequisite is the real gap.`;
      const outside = inScope(s, prereq) ? "" : ", outside the selection";
      addTrace(
        s,
        "trace_root_cause",
        `${concept.name} below threshold; testing prerequisite ${nameOf(prereq)}`,
        `Unresolved prerequisite of ${concept.name}: ${nameOf(prereq)} (${s.tested.has(prereq) ? pct(s.p[prereq]) : "untested"}${outside})`,
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
      `1 question on ${concept.name}`,
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
        `1 question on ${nameOf(other)}`,
      );
      next = [issue(s, other)];
    } else {
      s.stack.pop();
      explainRoot(parent, `Correct, so the prerequisites are fine. The gap is ${nameOf(parent)} itself. `);
    }
  } else {
    feedback = `Correct. ${concept.summary ?? ""}`.trim();
    const r = advance(s);
    action = r.action;
    next = r.questions;
  }

  return { correct, concept_id: cid, feedback, citation, mastery: masteryList(s), next_action: action, next_questions: next };
}

export async function getTrace(sessionId: string, afterStep: number): Promise<TraceResponse> {
  await sleep(150);
  const s = sessions.get(sessionId);
  return { events: s ? s.trace.filter((e) => e.step > afterStep) : [] };
}

export async function getNotes(sessionId: string): Promise<NotesResponse> {
  await sleep(500);
  const s = sessionOr404(sessionId);
  const reviewed = MOCK_CONCEPTS.filter((c) => inScope(s, c.id) || s.tested.has(c.id));
  const weak = new Set(reviewed.filter((c) => s.everWrong.has(c.id) || (s.tested.has(c.id) && s.p[c.id] < MASTERED)).map((c) => c.id));
  const mastered = reviewed.filter((c) => (s.p[c.id] ?? 0) >= MASTERED).length;

  const lines = [
    `# ${MOCK_LECTURE_TITLE}: review notes`,
    "",
    `**${mastered} of ${reviewed.length} concepts mastered** in ${s.answered} questions.`,
    "",
  ];
  if (weak.size) {
    lines.push("## Review these first", "");
    for (const c of reviewed.filter((c) => weak.has(c.id))) {
      const exp = EXPLANATIONS[c.id];
      lines.push(`### ${c.name} (slides p. ${c.pages.join(", ")})`, "", exp.text, "", `> Slide p. ${exp.page}: “${exp.quote}”`, "");
    }
  }
  lines.push(s.targets.length ? "## What you reviewed" : "## All concepts", "");
  for (const c of reviewed) {
    const icon = weak.has(c.id) ? "⚠️" : s.tested.has(c.id) ? "✅" : "⬜";
    lines.push(`- ${icon} **${c.name}** (p. ${c.pages.join(", ")}): ${c.summary}`);
  }

  const cards = reviewed
    .map((c) => ({ front: `Explain: ${c.name}`, back: c.summary ?? "", concept_id: c.id, page: c.pages[0] }))
    .sort((a, b) => Number(weak.has(b.concept_id)) - Number(weak.has(a.concept_id)));

  return { summary_markdown: lines.join("\n"), weak_concepts: [...weak], flashcards: cards };
}

export async function getFlashcardsCsv(sessionId: string): Promise<string> {
  const notes = await getNotes(sessionId);
  const esc = (v: string) => `"${v.replace(/"/g, '""')}"`;
  return notes.flashcards.map((f) => `${esc(f.front)},${esc(`${f.back} (slide p. ${f.page})`)}`).join("\n");
}
