import {
  answerPreservedAfterGuidedQuestion,
  buildElaborateQuestionRequest,
  buildGuidedQuestionRequest,
  canRestoreOriginalExplanation,
  captureElaborationFingerprint,
  explanationPanelsForConcept,
  shouldApplyElaborationResponse,
  shouldRenderGuidedQuestions,
  shouldShowElaborationFallback,
  shouldShowExplainDifferently,
  visibleGuidedQuestions,
} from "./guidedQuestions.ts";
import { en } from "../i18n/en.ts";
import { bg } from "../i18n/bg.ts";
import { presentTutorFeedback } from "./feedbackPresentation.ts";
import type { TutorSession } from "../types/tutor.ts";

function assert(
  condition: boolean,
  message: string,
): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

const multiplication = [
  {
    question_id: "unknown.factor.definition",
    label: "What is a factor?",
    category: "definition",
  },
  {
    question_id: "unknown.factor.identify_known",
    label: "How do I identify the known factor?",
    category: "understand_step",
  },
];

const bulgarian = [
  {
    question_id: "unknown.factor.definition",
    label: "Какво е множител?",
    category: "definition",
  },
];

assert(
  shouldRenderGuidedQuestions(multiplication),
  "Supported questions must render",
);
assert(
  shouldRenderGuidedQuestions([]) === false,
  "Empty list must render nothing",
);
assert(
  shouldRenderGuidedQuestions(undefined) === false,
  "Missing list must render nothing",
);

const visible = visibleGuidedQuestions([
  ...multiplication,
  ...multiplication,
  ...multiplication,
]);
assert(visible.length === 4, "At most four buttons are shown");
assert(
  visible[0].question_id === "unknown.factor.definition",
  "First displayed button keeps the server question_id",
);

const request = buildGuidedQuestionRequest(
  "unknown.factor.identify_known",
);
assert(
  request.question_id === "unknown.factor.identify_known",
  "Buttons must submit the stable question_id",
);
assert(
  request.question === undefined,
  "Guided requests must not send client-authored question text",
);

assert(
  answerPreservedAfterGuidedQuestion("12", "12"),
  "A partial numeric answer must stay in the answer field",
);

assert(
  en["tutor.hint"] === "Hint",
  "Existing Hint control copy remains",
);
assert(
  en["tutor.ask"] === "Ask a question",
  "Existing Ask a question control copy remains",
);
assert(
  en["tutor.guidedHeading"] === "Not sure where to start?",
  "English guided heading must be localized",
);
assert(
  bg["tutor.guidedHeading"] === "Не знаеш откъде да започнеш?",
  "Bulgarian guided heading must be localized",
);
assert(
  bulgarian[0].label === "Какво е множител?",
  "Bulgarian suggested labels come from the session language",
);

const afterStep = visibleGuidedQuestions([
  {
    question_id: "unknown.factor.find_unknown",
    label: "How do I find the unknown factor?",
    category: "explain_method",
  },
]);
assert(
  afterStep[0].question_id === "unknown.factor.find_unknown",
  "Step changes replace the displayed question set",
);

const loading = presentTutorFeedback({
  questionLoading: true,
  status: "waiting_for_answer",
  feedback: "Find x",
  suggestion: null,
  lastGraded: null,
});
assert(
  loading.loadingExplanation,
  "Guided questions reuse the existing loading explanation state",
);

const explained = presentTutorFeedback({
  questionLoading: false,
  status: "concept",
  feedback: "A factor is a number that is multiplied.",
  suggestion: "Continue with the step.",
  lastGraded: null,
});
assert(
  explained.explanation !== null,
  "Guided answers reuse the existing explanation panel",
);
assert(
  explained.showExplanationHeading === false,
  "Guided answers must not add a second explanation heading",
);

const errorCopy = en["error.generic"];
assert(
  typeof errorCopy === "string" && errorCopy.length > 0,
  "Existing error display copy remains available",
);

function makeSession(
  overrides: Partial<TutorSession> = {},
): TutorSession {
  return {
    session_id: "session-1",
    problem_id: "story-1",
    problem_title: "Bottles",
    problem_statement: "Bottles were taken out.",
    status: "concept",
    feedback: "Doubled means multiplied by 2.",
    current_step: 1,
    total_steps: 3,
    completed: false,
    hint_available: true,
    expected_input_type: "number",
    suggestion: "Continue with the step.",
    metadata: {
      guided_question: true,
      guided_question_id: "story.phrase.doubled",
      guided_local_explanation: "Doubled means multiplied by 2.",
      elaboration_available: true,
    },
    ...overrides,
  };
}

const available = makeSession();
assert(
  shouldShowExplainDifferently(available),
  "Explain differently appears after a supported local explanation",
);
assert(
  shouldShowExplainDifferently(
    makeSession({
      metadata: {
        guided_question: true,
        guided_question_id: "story.phrase.doubled",
        elaboration_available: false,
      },
    }),
  ) === false,
  "The button is hidden when the server does not offer elaboration",
);
assert(
  shouldShowExplainDifferently(
    makeSession({
      status: "waiting_for_answer",
      metadata: { elaboration_available: true },
    }),
  ) === false,
  "The button is hidden before a Guided Question explanation",
);

const elaborateRequest = buildElaborateQuestionRequest(
  "story.phrase.doubled",
);
assert(
  elaborateRequest.question_id === "story.phrase.doubled",
  "Explain differently reuses the live question_id",
);
assert(
  elaborateRequest.explanation_mode === "elaborate",
  "Explain differently sends explanation_mode=elaborate",
);
assert(
  elaborateRequest.question === undefined,
  "Elaboration must not send client-authored explanation text",
);

assert(
  en["tutor.explainDifferently"] === "Explain differently",
  "English elaboration label is localized",
);
assert(
  bg["tutor.explainDifferently"] === "Обясни по друг начин",
  "Bulgarian elaboration label is localized",
);

const keepLocalWhileWaiting = presentTutorFeedback({
  questionLoading: false,
  status: "concept",
  feedback: "Doubled means multiplied by 2.",
  suggestion: "Continue with the step.",
  lastGraded: null,
});
assert(
  keepLocalWhileWaiting.explanation?.text ===
    "Doubled means multiplied by 2.",
  "Elaboration loading must keep the local explanation visible",
);
assert(
  keepLocalWhileWaiting.showExplanationHeading === false,
  "Elaboration must not add a second explanation heading",
);
assert(
  explanationPanelsForConcept() === 1,
  "Elaboration reuses the single explanation panel",
);

const replaced = makeSession({
  feedback:
    "Imagine a row of bottles, then put another row of the same length next to it.",
  metadata: {
    ...available.metadata,
    elaboration_status: "applied",
    guided_local_explanation: "Doubled means multiplied by 2.",
  },
});
assert(
  canRestoreOriginalExplanation(replaced),
  "A successful alternative can restore the original explanation",
);

const failed = makeSession({
  metadata: {
    ...available.metadata,
    elaboration_status: "failed",
  },
});
assert(
  shouldShowElaborationFallback(failed),
  "Failed elaboration keeps a non-blocking fallback note",
);
assert(
  failed.feedback === "Doubled means multiplied by 2.",
  "Failed elaboration keeps the original local explanation",
);

assert(
  answerPreservedAfterGuidedQuestion("18", "18"),
  "Numeric input stays in the field during elaboration",
);

const fingerprint = captureElaborationFingerprint(
  available,
  "story.phrase.doubled",
);
const advanced = makeSession({ current_step: 2 });
assert(
  shouldApplyElaborationResponse(
    fingerprint,
    advanced,
    replaced,
  ) === false,
  "A late elaboration response for a previous step is ignored",
);
assert(
  shouldApplyElaborationResponse(
    fingerprint,
    available,
    replaced,
  ),
  "A matching elaboration response replaces the explanation body",
);

console.log("guidedQuestions tests passed");
