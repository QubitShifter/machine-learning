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
  | "complete"
  | "concept";

export interface TutorSource {
  title: string;
  url: string;
  domain?: string | null;
}

export interface SuggestedQuestion {
  question_id: string;
  label: string;
  category: string;
}

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
  sources?: TutorSource[];
  suggested_questions?: SuggestedQuestion[];
  metadata: Record<string, unknown>;
}

export interface StartSessionRequest {
  problem_id: string;
  student_id?: string;
  language?: "en" | "bg";
}

export interface AnswerRequest {
  answer: string;
  input_type?: InputType;
  metadata?: Record<string, unknown>;
}

export interface QuestionRequest {
  question?: string;
  question_id?: string;
  explanation_mode?: "local" | "elaborate";
}

export interface CatalogTopic {
  id: string;
  name: string;
  available_problem_count: number;
  problem_ids: string[];
  generation_available: boolean;
  supported_difficulties: number[];
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
  generated: boolean;
  generation_available: boolean;
  supported_difficulties: number[];
}

export interface ProblemDetail extends ProblemSummary {
  problem_text: string;
  language: string;
  skills: string[];
  metadata: Record<string, unknown>;
}

export interface GenerateProblemRequest {
  subject: string;
  domain: string;
  topic: string;
  difficulty: number;
  seed?: number;
  language?: "en" | "bg";
  family?: string;
}

export interface AdaptiveRecommendationRequest {
  subject?: string;
  domain?: string;
  student_id?: string;
}

export interface AdaptiveRecommendation {
  recommendation_available: boolean;
  reason: string;
  subject: string | null;
  domain: string | null;
  topic: string | null;
  topic_name: string | null;
  difficulty: number | null;
  mastery: number | null;
  mastery_key: string | null;
  generation_available: boolean;
  problem_id: string | null;
  metadata: Record<string, unknown>;
}

export interface TopicProgress {
  subject: string;
  domain: string;
  topic: string;
  topic_name: string;
  mastery_key: string;
  mastery: number;
  mastery_label: string;
  questions_completed: number;
  first_attempt_streak: number;
  last_total_attempts: number;
  last_incorrect_attempts: number;
  last_hints_used: number;
  last_first_attempt_success: boolean;
  last_completed: boolean;
  generation_available: boolean;
  supported_difficulties: number[];
  recommended_difficulty: number | null;
  problem_id: string | null;
  recent_session_count: number;
  recent_first_attempt_success_rate: number;
  recent_hint_rate: number;
  recent_incorrect_rate: number;
  recent_average_attempts_per_step: number;
  recent_trend: string;
  metadata: Record<string, unknown>;
}

export interface StudentProgress {
  student_id: string;
  topics: TopicProgress[];
  recommendation: AdaptiveRecommendation;
  metadata: Record<string, unknown>;
}
