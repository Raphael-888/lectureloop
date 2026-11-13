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
  error?: string | null;
  title?: string;
  page_count?: number;
  overview?: string; // Markdown, empty until ready
  concepts: Concept[];
}

export interface LecturePage {
  page: number;
  title: string;
  page_type: string;
  text: string;
  concept_ids: string[];
}

export interface PagesResponse {
  lecture_id: string;
  pages: LecturePage[];
}

export interface SessionResponse {
  session_id: string;
  questions: Question[];
}

export type Difficulty = "easier" | "same" | "harder";

export interface Preferences {
  question_type: QuestionType | null; // null = the agent decides
  difficulty: Difficulty;
}

export interface ChatMessage {
  role: "student" | "tutor";
  text: string;
  time?: string;
}

export interface SessionState {
  session_id: string;
  lecture_id: string;
  concept_ids: string[];
  scope_summary: string; // Markdown
  preferences: Preferences;
  chat: ChatMessage[];
  current_question: Question | null;
  mastery: Mastery[];
  answered: number;
  done: boolean;
}

export interface ChatResponse {
  reply: string;
  preferences: Preferences;
  changed: string[]; // "question_type" | "difficulty"
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

// ---------- Nov 12: main page colours, bookmarks, quiz settings ----------

export interface LectureMastery {
  lecture_id: string;
  mastery: Mastery[];
  sessions: number;
}

export interface BookmarkItem {
  question: Question;
  concept_name: string;
  your_answer?: string | null;
  correct?: boolean | null;
  added_at: string;
  session_id: string;
}

export interface BookmarksResponse {
  lecture_id: string;
  items: BookmarkItem[];
}

export interface PreferencesUpdate {
  question_type?: QuestionType;
  difficulty?: Difficulty;
  clear_question_type?: boolean;
}
