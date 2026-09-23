import type { TutorSession } from "../types/tutor.ts";
import {
  AUTOMATIC_FAMILY,
  LOGICAL_REASONING_FAMILIES,
  LOGICAL_REASONING_TOPIC,
  buildGenerateProblemRequest,
  catalogPanelState,
  exerciseStatementForDisplay,
  familySelectionForTopic,
  formatLogicalReasoningStatement,
  isLogicalReasoningFamily,
  isLogicalReasoningTopic,
  readGeneratedFamily,
} from "./logicalReasoning.ts";
import {
  answerPreservedAfterHint,
  feedbackPanelKey,
  hintButtonDisabled,
} from "../components/hintControls.ts";
import {
  buildGuidedQuestionRequest,
  visibleGuidedQuestions,
} from "../components/guidedQuestions.ts";
import { catalogDisplayName, translate } from "../i18n/index.ts";

function assert(
  condition: boolean,
  message: string,
): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

assert(
  LOGICAL_REASONING_FAMILIES.join(",") ===
    "number_detective,distribution_puzzles,logic_detective",
  "All three Stage G family identifiers must be available",
);
assert(
  isLogicalReasoningTopic(LOGICAL_REASONING_TOPIC),
  "logical_reasoning is the catalog topic id",
);
assert(
  isLogicalReasoningFamily("number_detective") &&
    isLogicalReasoningFamily("distribution_puzzles") &&
    isLogicalReasoningFamily("logic_detective"),
  "Family identifiers must match the backend contract",
);
assert(
  isLogicalReasoningFamily("Surprise me") === false,
  "Translated labels must never be treated as family ids",
);

const sharedFields = {
  subject: "mathematics",
  domain: "primary_school",
  difficulty: 2,
  language: "en" as const,
};

const explicit = buildGenerateProblemRequest({
  ...sharedFields,
  topic: LOGICAL_REASONING_TOPIC,
  family: "distribution_puzzles",
});
assert(
  explicit.family === "distribution_puzzles",
  "An explicit family must be sent as the backend identifier",
);
assert(
  explicit.subject === "mathematics" &&
    explicit.domain === "primary_school" &&
    explicit.topic === "logical_reasoning" &&
    explicit.difficulty === 2 &&
    explicit.language === "en",
  "Generation must keep the existing required request fields",
);

const automatic = buildGenerateProblemRequest({
  ...sharedFields,
  topic: LOGICAL_REASONING_TOPIC,
  family: AUTOMATIC_FAMILY,
});
assert(
  automatic.family === undefined,
  "Automatic selection must omit family",
);
assert(
  JSON.stringify(automatic).includes('"family"') === false,
  "Automatic selection must not serialize a family field",
);

const surpriseLabel = buildGenerateProblemRequest({
  ...sharedFields,
  topic: LOGICAL_REASONING_TOPIC,
  family: "Surprise me",
});
assert(
  surpriseLabel.family === undefined,
  "The Surprise me label must never be sent as family",
);

const arithmetic = buildGenerateProblemRequest({
  ...sharedFields,
  topic: "arithmetic",
  family: "number_detective",
});
assert(
  arithmetic.family === undefined,
  "Other topics must not send a stale family",
);

const recommended = buildGenerateProblemRequest({
  ...sharedFields,
  topic: LOGICAL_REASONING_TOPIC,
  family: "logic_detective",
});
assert(
  recommended.family === "logic_detective",
  "Recommended practice must pass a validated family",
);

const recommendedOtherTopic = buildGenerateProblemRequest({
  ...sharedFields,
  topic: "arithmetic",
  family: "logic_detective",
});
assert(
  recommendedOtherTopic.family === undefined,
  "Recommended practice must omit family for other topics",
);

const recommendedInvalid = buildGenerateProblemRequest({
  ...sharedFields,
  topic: LOGICAL_REASONING_TOPIC,
  family: "unsupported_family",
});
assert(
  recommendedInvalid.family === undefined,
  "Recommended practice must ignore unsupported family ids",
);

const explicitWithSeedIntent = buildGenerateProblemRequest({
  ...sharedFields,
  topic: LOGICAL_REASONING_TOPIC,
  family: "logic_detective",
});
assert(
  explicitWithSeedIntent.family === "logic_detective",
  "An explicit family remains authoritative when a seed is also used",
);

assert(
  familySelectionForTopic("arithmetic", "number_detective") ===
    AUTOMATIC_FAMILY,
  "Switching topics must clear stale family selection",
);
assert(
  familySelectionForTopic(
    LOGICAL_REASONING_TOPIC,
    "logic_detective",
  ) === "logic_detective",
  "Staying on Logical Reasoning must keep the chosen family",
);

const bulgarianFamily = "number_detective";
assert(
  bulgarianFamily === "number_detective",
  "Language switching must preserve internal family identifiers",
);
assert(
  translate("bg", "path.family.number_detective") !==
    bulgarianFamily,
  "Bulgarian labels are display-only",
);

assert(
  catalogDisplayName(
    "topic",
    "logical_reasoning",
    "Logical Reasoning",
    "en",
  ) === "Logical Reasoning",
  "English Logical Reasoning catalog label",
);
assert(
  catalogDisplayName(
    "topic",
    "logical_reasoning",
    "Logical Reasoning",
    "bg",
  ) === "Логическо мислене",
  "Bulgarian Logical Reasoning catalog label",
);
assert(
  catalogDisplayName(
    "topic",
    "arithmetic",
    "Arithmetic",
    "en",
  ) === "Arithmetic",
  "Existing Arithmetic topic remains available",
);
assert(
  catalogDisplayName(
    "topic",
    "story_problems",
    "Story Problems",
    "bg",
  ) === "Сюжетни задачи",
  "Existing Story Problems topic remains available",
);

const progressTopicIds = [
  "arithmetic",
  "unknown_numbers",
  "number_patterns",
  "word_problems",
  "story_problems",
  "logical_reasoning",
] as const;
const progressLabelsEn = progressTopicIds.map((id) =>
  catalogDisplayName("topic", id, id, "en"),
);
const progressLabelsBg = progressTopicIds.map((id) =>
  catalogDisplayName("topic", id, id, "bg"),
);
assert(
  progressLabelsEn.includes("Logical Reasoning") &&
    new Set(progressLabelsEn).size === progressTopicIds.length,
  "Logical Reasoning is a distinct English progress category",
);
assert(
  progressLabelsBg.includes("Логическо мислене") &&
    new Set(progressLabelsBg).size === progressTopicIds.length,
  "Logical Reasoning is a distinct Bulgarian progress category",
);
assert(
  catalogDisplayName(
    "topic",
    "logical_reasoning",
    "Logical Reasoning",
    "en",
  ) !==
    catalogDisplayName(
      "topic",
      "word_problems",
      "Word Problems",
      "en",
    ),
  "Logical Reasoning must not reuse the Word Problems progress label",
);

const clues =
  "The sum of the digits is 6. The tens digit is 4 greater than the units digit. Find the two-digit number.";
const formatted = formatLogicalReasoningStatement(clues);
assert(
  formatted.includes("\n") && formatted.includes("\n\n") === false,
  "Logical Reasoning clues must wrap onto separate lines",
);
assert(
  formatted.indexOf("The sum of the digits is 6.") <
    formatted.indexOf("Find the two-digit number."),
  "Clue order must be preserved",
);
assert(
  exerciseStatementForDisplay(clues, {
    topic: "story_problems",
  }) === clues,
  "Story problem statements must not be rewritten",
);
assert(
  exerciseStatementForDisplay(clues, {
    problemId: "grade4_logical_reasoning_generated_abc",
  }) === formatted,
  "Tutor sessions identify Logical Reasoning by generated id",
);
assert(
  readGeneratedFamily({ family: "logic_detective" }) ===
    "logic_detective",
  "Generated metadata family must be readable after creation",
);

assert(
  catalogPanelState(null, true) === "loading",
  "Catalog loading is shown only while a request is in flight",
);
assert(
  catalogPanelState(null, false) === "error",
  "A failed catalog request must leave the loading state",
);
assert(
  catalogPanelState({ subjects: [] }, false) === "ready",
  "A loaded catalog is ready even if empty",
);

const logicQuestions = [
  {
    question_id: "logic.known",
    label: "What information is given?",
    category: "understand_step",
  },
  {
    question_id: "logic.eliminate",
    label: "How can I eliminate impossible possibilities?",
    category: "strategy",
  },
];
assert(
  visibleGuidedQuestions(logicQuestions)[0].question_id ===
    "logic.known",
  "Guided Questions must use server-provided ids",
);
assert(
  buildGuidedQuestionRequest("logic.eliminate").question_id ===
    "logic.eliminate",
  "Guided Question clicks must submit the server id",
);

function session(overrides: Partial<TutorSession> = {}): TutorSession {
  return {
    session_id: "logic-session",
    problem_id: "grade4_logical_reasoning_generated_abcd",
    problem_title: "Number Detective",
    problem_statement: clues,
    status: "waiting_for_answer",
    feedback: "What is the units digit?",
    current_step: 1,
    total_steps: 3,
    completed: false,
    hint_available: true,
    expected_input_type: "number",
    suggestion: null,
    suggested_questions: logicQuestions,
    metadata: {},
    ...overrides,
  };
}

assert(
  feedbackPanelKey(
    session({
      status: "hint",
      feedback: "Use the clue about the digits.",
      metadata: { hint_level: 1, hints_used_on_step: 1 },
    }),
  ) !==
    feedbackPanelKey(
      session({
        status: "hint",
        feedback: "Look for two digits with the stated difference.",
        metadata: { hint_level: 2, hints_used_on_step: 2 },
      }),
    ),
  "The second hint must replace the first hint",
);
assert(
  hintButtonDisabled(
    session({
      hint_available: false,
      metadata: {
        hint_exhausted: true,
        hints_used_on_step: 3,
        hint_level: 3,
      },
    }),
  ),
  "The final hint disables further requests",
);
const afterGuidedQuestion = session({
  status: "concept",
  hint_available: false,
  feedback: "The clues already given in the statement.",
  metadata: {
    concept_question: true,
    answer_source: "local",
    guided_question: true,
    guided_question_id: "logic.known",
  },
});
assert(
  Object.prototype.hasOwnProperty.call(
    afterGuidedQuestion.metadata,
    "hint_level",
  ) === false,
  "Guided Question responses may omit hint_level",
);
assert(
  hintButtonDisabled(afterGuidedQuestion),
  "Guided Questions must not re-enable an exhausted hint button",
);
assert(
  hintButtonDisabled(
    session({
      current_step: 2,
      status: "correct",
      hint_available: true,
      metadata: {},
    }),
  ) === false,
  "Advancing to the next step restores the first hint",
);
assert(
  answerPreservedAfterHint("1", "1"),
  "An incorrect or hint interaction keeps the typed number",
);
assert(
  session({ current_step: 1 }).current_step === 1 &&
    session({ current_step: 3, total_steps: 5 }).total_steps === 5,
  "Variable step counts remain backend-driven",
);

console.log("logical_reasoning frontend tests passed");
