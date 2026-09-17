export interface GradedFeedback {
  status: string;
  feedback: string;
  suggestion: string | null;
}

export interface FeedbackPresentation {
  loadingExplanation: boolean;
  explanation: {
    text: string;
    suggestion: string | null;
  } | null;
  graded: GradedFeedback | null;
  showGradedAsLastAnswer: boolean;
  showExplanationHeading: boolean;
  useDefaultPanel: boolean;
  defaultStatus: string;
  defaultFeedback: string;
  defaultSuggestion: string | null;
}

const GRADE_STATUSES = new Set([
  "correct",
  "incorrect",
  "hint",
]);

export function isGradeStatus(status: string) {
  return GRADE_STATUSES.has(status);
}

export function snapshotGradedFeedback(session: {
  status: string;
  feedback: string;
  suggestion: string | null;
}): GradedFeedback | null {
  if (!isGradeStatus(session.status)) {
    return null;
  }

  return {
    status: session.status,
    feedback: session.feedback,
    suggestion: session.suggestion,
  };
}

export function presentTutorFeedback(input: {
  questionLoading: boolean;
  status: string;
  feedback: string;
  suggestion: string | null;
  lastGraded: GradedFeedback | null;
}): FeedbackPresentation {
  const loadingExplanation = input.questionLoading;
  const isConcept = input.status === "concept";
  const splitView = loadingExplanation || isConcept;
  const currentGrade = isGradeStatus(input.status)
    ? {
        status: input.status,
        feedback: input.feedback,
        suggestion: input.suggestion,
      }
    : null;
  const graded = splitView
    ? input.lastGraded ?? currentGrade
    : currentGrade ?? input.lastGraded;

  return {
    loadingExplanation,
    explanation: isConcept
      ? {
          text: input.feedback,
          suggestion: input.suggestion,
        }
      : null,
    graded: splitView ? graded : null,
    showGradedAsLastAnswer: splitView && graded !== null,
    showExplanationHeading: false,
    useDefaultPanel: !splitView,
    defaultStatus: input.status,
    defaultFeedback: input.feedback,
    defaultSuggestion: input.suggestion,
  };
}

export function questionStatusIsPendingGrade(
  presentation: FeedbackPresentation,
) {
  return (
    presentation.loadingExplanation &&
    presentation.defaultStatus === "correct"
  );
}
