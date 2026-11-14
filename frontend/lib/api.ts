// The ONLY place the frontend talks to the backend.
// Every page imports from here, so switching mock <-> real backend is one setting.

import { USE_MOCK } from "./config";
import * as mock from "./mock/engine";
import type {
  AnswerResponse,
  BookmarksResponse,
  ChatResponse,
  ConceptsResponse,
  LectureMastery,
  NotesResponse,
  PagesResponse,
  PreferencesUpdate,
  SessionResponse,
  SessionState,
  TraceResponse,
  UploadResponse,
} from "./types";

const BASE = "/api";

export class ApiError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

export function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ApiError("network_error", "Cannot reach the backend. Is it running?");
  }
  if (!res.ok) {
    let code = `http_${res.status}`;
    let message = res.statusText || "Request failed";
    try {
      const body = await res.json();
      if (body?.error) {
        code = body.error.code ?? code;
        message = body.error.message ?? message;
      }
    } catch {
      // response was not JSON; keep the HTTP status text
    }
    throw new ApiError(code, message);
  }
  return (await res.json()) as T;
}

function postJson(body: unknown): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

const enc = encodeURIComponent;

// 1. Upload a lecture PDF. `null` = demo lecture (mock mode only).
export function uploadLecture(file: File | null): Promise<UploadResponse> {
  if (USE_MOCK) return mock.uploadLecture(file);
  if (!file) throw new ApiError("no_file", "Please choose a PDF first.");
  const form = new FormData();
  form.append("file", file);
  return request<UploadResponse>("/lectures", { method: "POST", body: form });
}

// 2. Concepts + overview (poll until status is "ready").
export function getConcepts(lectureId: string): Promise<ConceptsResponse> {
  if (USE_MOCK) return mock.getConcepts(lectureId);
  return request<ConceptsResponse>(`/lectures/${enc(lectureId)}/concepts`);
}

// 2b. Slide pages for the "original PDF" view; conceptIds filters to their pages.
export function getPages(lectureId: string, conceptIds: string[] = []): Promise<PagesResponse> {
  if (USE_MOCK) return mock.getPages(lectureId, conceptIds);
  const q = conceptIds.length ? `?concept_ids=${enc(conceptIds.join(","))}` : "";
  return request<PagesResponse>(`/lectures/${enc(lectureId)}/pages${q}`);
}

// 2b. One slide as it looks in the PDF. Mock mode serves the demo lecture's pages (M04, rendered
// to public/mock-pages/<page>.jpg); anything else falls back to the page's text.
const MOCK_PAGE_IMAGES = 36;
export function pageImageUrl(lectureId: string, page: number): string | null {
  if (USE_MOCK) return page >= 1 && page <= MOCK_PAGE_IMAGES ? `/mock-pages/${page}.jpg` : null;
  return `${BASE}/lectures/${enc(lectureId)}/pages/${page}/image`;
}

// 2a. Mastery across every session of the lecture (colours the concept boxes).
export function getLectureMastery(lectureId: string): Promise<LectureMastery> {
  if (USE_MOCK) return mock.getLectureMastery(lectureId);
  return request<LectureMastery>(`/lectures/${enc(lectureId)}/mastery`);
}

// 2c. Bookmarks ("mistake book"): list, and toggle the star on one question.
export function getBookmarks(lectureId: string): Promise<BookmarksResponse> {
  if (USE_MOCK) return mock.getBookmarks(lectureId);
  return request<BookmarksResponse>(`/lectures/${enc(lectureId)}/bookmarks`);
}

export function toggleBookmark(lectureId: string, questionId: string, sessionId: string): Promise<BookmarksResponse> {
  if (USE_MOCK) return mock.toggleBookmark(lectureId, questionId, sessionId);
  return request<BookmarksResponse>(
    `/lectures/${enc(lectureId)}/bookmarks`,
    postJson({ question_id: questionId, session_id: sessionId }),
  );
}

// 3. Start a review session on the selected concepts (empty = whole lecture).
export function startSession(lectureId: string, conceptIds: string[]): Promise<SessionResponse> {
  if (USE_MOCK) return mock.startSession(lectureId, conceptIds);
  return request<SessionResponse>(
    "/sessions",
    postJson({ lecture_id: lectureId, concept_ids: conceptIds }),
  );
}

// 3b. Everything a page needs after a reload.
export function getSession(sessionId: string): Promise<SessionState> {
  if (USE_MOCK) return mock.getSession(sessionId);
  return request<SessionState>(`/sessions/${enc(sessionId)}`);
}

// 3d. The question-type / difficulty picker, and the End button.
export function setPreferences(sessionId: string, update: PreferencesUpdate): Promise<SessionState> {
  if (USE_MOCK) return mock.setPreferences(sessionId, update);
  return request<SessionState>(`/sessions/${enc(sessionId)}/preferences`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(update),
  });
}

export function finishSession(sessionId: string): Promise<SessionState> {
  if (USE_MOCK) return mock.finishSession(sessionId);
  return request<SessionState>(`/sessions/${enc(sessionId)}/finish`, { method: "POST" });
}

// 3c. Tutor chat: a question about the material, or an instruction about the quiz.
export function chat(sessionId: string, message: string): Promise<ChatResponse> {
  if (USE_MOCK) return mock.chat(sessionId, message);
  return request<ChatResponse>(`/sessions/${enc(sessionId)}/chat`, postJson({ message }));
}

// 4. Submit one answer.
export function submitAnswer(
  sessionId: string,
  questionId: string,
  answer: string,
): Promise<AnswerResponse> {
  if (USE_MOCK) return mock.submitAnswer(sessionId, questionId, answer);
  return request<AnswerResponse>(
    "/answers",
    postJson({ session_id: sessionId, question_id: questionId, answer }),
  );
}

// 5. Agent trace events after a given step (shown in the collapsed "agent reasoning" panel).
export function getTrace(sessionId: string, afterStep: number): Promise<TraceResponse> {
  if (USE_MOCK) return mock.getTrace(sessionId, afterStep);
  return request<TraceResponse>(`/sessions/${enc(sessionId)}/trace?after_step=${afterStep}`);
}

// 6. Notes and flashcards.
export function getNotes(sessionId: string): Promise<NotesResponse> {
  if (USE_MOCK) return mock.getNotes(sessionId);
  return request<NotesResponse>(`/sessions/${enc(sessionId)}/notes`);
}

// Returns a URL the browser can download the Anki CSV from.
export async function getFlashcardsCsvUrl(sessionId: string): Promise<string> {
  if (USE_MOCK) {
    const csv = await mock.getFlashcardsCsv(sessionId);
    return URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  }
  return `${BASE}/sessions/${enc(sessionId)}/flashcards.csv`;
}
