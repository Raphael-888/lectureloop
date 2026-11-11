// Types mirror docs/api-contract.md. If the contract changes, update this file.

export interface Concept {
  id: string;
  name: string;
  summary?: string;
  pages: number[];
  prerequisites: string[]; // ids of DIRECT prerequisite concepts
}

export type QuestionType = "multiple_choice" | "short_answer";

export interface Question {
  id: string;
  concept_id: string;
  type: QuestionType;
  prompt: string;
  options?: string[]; // only for multiple_choice, e.g. "B. Bottom-up"
}

export type MasteryLabel = "mastered" | "confused" | "not_mastered" | "untested";

export interface Mastery {
  concept_id: string;
  p_mastery: number; // 0–1, from BKT
  label: MasteryLabel;
}

export interface TraceEvent {
  step: number;
  time: string; // ISO timestamp
  tool: string;
  reason: string;
  summary: string;
}

export type LectureStatus = "processing" | "ready" | "failed";

export interface UploadResponse {
  lecture_id: string;
  status: LectureStatus;
}

export interface ConceptsResponse {
  lecture_id: string;
  status: LectureStatus;
  concepts: Concept[];
}

export interface SessionResponse {
  session_id: string;
  questions: Question[];
}

export interface Citation {
  page: number;
  quote: string;
}

export type NextAction = "next_question" | "explain" | "test_prerequisite" | "done";

export interface AnswerResponse {
  correct: boolean;
  concept_id: string;
  feedback: string;
  citation?: Citation | null;
  mastery: Mastery[];
  next_action: NextAction;
  next_questions: Question[];
}

export interface TraceResponse {
  events: TraceEvent[];
}

export interface Flashcard {
  front: string;
  back: string;
  concept_id: string;
  page: number;
}

export interface NotesResponse {
  summary_markdown: string;
  weak_concepts: string[];
  flashcards: Flashcard[];
}
