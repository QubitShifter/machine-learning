export type InputType =
  | "text"
  | "number"
  | "math"
  | "latex"
  | "multiple_choice"
  | "vector"
  | "matrix"
  | "units";

export type TutorStatus =
  | "waiting_for_answer"
  | "correct"
  | "incorrect"
  | "hint"
  | "complete";

export interface TutorSession {
  session_id: string;
  problem_id: string;
  problem_title: string;
  problem_statement: string;
  status: TutorStatus | string;
  feedback: string;
  current_step: number;
  total_steps: number;
  completed: boolean;
  hint_available: boolean;
  expected_input_type: InputType;
  suggestion: string | null;
  metadata: Record<string, unknown>;
}

export interface StartSessionRequest {
  problem_id: string;
}

export interface AnswerRequest {
  answer: string;
  input_type?: InputType;
  metadata?: Record<string, unknown>;
}

export interface CatalogTopic {
  id: string;
  name: string;
  available_problem_count: number;
  problem_ids: string[];
}

export interface CatalogDomain {
  id: string;
  name: string;
  available_problem_count: number;
  topics: CatalogTopic[];
}

export interface CatalogSubject {
  id: string;
  name: string;
  available_problem_count: number;
  domains: CatalogDomain[];
}

export interface CatalogResponse {
  subjects: CatalogSubject[];
}

export interface ProblemSummary {
  problem_id: string;
  title: string;
  subject: string;
  domain: string;
  topic: string;
  problem_type: string;
  available: boolean;
  grade: number | null;
  total_steps: number;
  expected_input_type: InputType;
}

export interface ProblemDetail extends ProblemSummary {
  problem_text: string;
  language: string;
  skills: string[];
  metadata: Record<string, unknown>;
}
