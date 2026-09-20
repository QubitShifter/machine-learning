import type {
  QuestionRequest,
  SuggestedQuestion,
  TutorSession,
} from "@/types/tutor";

export const MAX_GUIDED_QUESTIONS = 4;

export const ELABORATION_FALLBACK_STATUSES = new Set([
  "off",
  "unavailable",
  "unsupported",
  "failed",
  "stale",
  "duplicate",
]);

export interface ElaborationFingerprint {
  session_id: string;
  problem_id: string;
  current_step: number;
  question_id: string;
}

export function shouldRenderGuidedQuestions(
  questions: SuggestedQuestion[] | undefined | null,
): boolean {
  return Array.isArray(questions) && questions.length > 0;
}

export function visibleGuidedQuestions(
  questions: SuggestedQuestion[] | undefined | null,
  limit = MAX_GUIDED_QUESTIONS,
): SuggestedQuestion[] {
  if (!Array.isArray(questions) || questions.length === 0) {
    return [];
  }

  return questions.slice(0, limit);
}

export function buildGuidedQuestionRequest(
  questionId: string,
): QuestionRequest {
  return {
    question_id: questionId,
  };
}

export function buildElaborateQuestionRequest(
  questionId: string,
): QuestionRequest {
  return {
    question_id: questionId,
    explanation_mode: "elaborate",
  };
}

export function answerPreservedAfterGuidedQuestion(
  answerBefore: string,
  answerAfter: string,
): boolean {
  return answerBefore === answerAfter;
}

function readMetadataString(
  session: TutorSession | null | undefined,
  key: string,
): string | null {
  if (!session) {
    return null;
  }

  const value = session.metadata?.[key];
  return typeof value === "string" && value.length > 0
    ? value
    : null;
}

export function guidedQuestionId(
  session: TutorSession | null | undefined,
): string | null {
  return readMetadataString(session, "guided_question_id");
}

export function guidedLocalExplanation(
  session: TutorSession | null | undefined,
): string | null {
  return readMetadataString(session, "guided_local_explanation");
}

export function shouldShowExplainDifferently(
  session: TutorSession | null | undefined,
): boolean {
  if (!session || session.status !== "concept") {
    return false;
  }

  return (
    session.metadata?.elaboration_available === true &&
    session.metadata?.guided_question === true &&
    guidedQuestionId(session) !== null
  );
}

export function captureElaborationFingerprint(
  session: TutorSession,
  questionId: string,
): ElaborationFingerprint {
  return {
    session_id: session.session_id,
    problem_id: session.problem_id,
    current_step: session.current_step,
    question_id: questionId,
  };
}

export function isElaborationResponseStale(
  fingerprint: ElaborationFingerprint,
  activeSession: TutorSession | null | undefined,
): boolean {
  if (!activeSession) {
    return true;
  }

  return (
    activeSession.session_id !== fingerprint.session_id ||
    activeSession.problem_id !== fingerprint.problem_id ||
    activeSession.current_step !== fingerprint.current_step
  );
}

export function shouldApplyElaborationResponse(
  fingerprint: ElaborationFingerprint,
  activeSession: TutorSession | null | undefined,
  response: TutorSession,
): boolean {
  if (isElaborationResponseStale(fingerprint, activeSession)) {
    return false;
  }

  return (
    response.session_id === fingerprint.session_id &&
    response.problem_id === fingerprint.problem_id &&
    response.current_step === fingerprint.current_step
  );
}

export function elaborationStatus(
  session: TutorSession | null | undefined,
): string | null {
  return readMetadataString(session, "elaboration_status");
}

export function shouldShowElaborationFallback(
  session: TutorSession | null | undefined,
): boolean {
  const status = elaborationStatus(session);
  return (
    status !== null && ELABORATION_FALLBACK_STATUSES.has(status)
  );
}

export function canRestoreOriginalExplanation(
  session: TutorSession | null | undefined,
): boolean {
  const original = guidedLocalExplanation(session);
  return (
    original !== null &&
    session !== null &&
    session !== undefined &&
    session.feedback !== original
  );
}

export function explanationPanelsForConcept(): number {
  return 1;
}
