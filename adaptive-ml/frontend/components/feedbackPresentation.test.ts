import {
  presentTutorFeedback,
  questionStatusIsPendingGrade,
  snapshotGradedFeedback,
} from "./feedbackPresentation.ts";

function assert(
  condition: boolean,
  message: string,
): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

const previousCorrect = snapshotGradedFeedback({
  status: "correct",
  feedback: "Correct. You found the integrating factor.",
  suggestion: "Next, multiply by mu(x).",
});

assert(
  previousCorrect?.status === "correct",
  "A correct mathematical answer can be snapshotted",
);
assert(
  snapshotGradedFeedback({
    status: "concept",
    feedback: "An explanation",
    suggestion: null,
  }) === null,
  "Conceptual explanations must not be stored as graded answers",
);

const loadingOverCorrect = presentTutorFeedback({
  questionLoading: true,
  status: "correct",
  feedback: "Correct. You found the integrating factor.",
  suggestion: "Next, multiply by mu(x).",
  lastGraded: previousCorrect,
});

assert(
  loadingOverCorrect.loadingExplanation === true,
  "Question loading must show the explanation loading state",
);
assert(
  loadingOverCorrect.explanation === null,
  "The pending question must not reuse the previous explanation text",
);
assert(
  loadingOverCorrect.useDefaultPanel === false,
  "Loading must not keep the default graded-feedback layout",
);
assert(
  loadingOverCorrect.showGradedAsLastAnswer === true,
  "Previous mathematical feedback stays available as the last answer",
);
assert(
  loadingOverCorrect.graded?.status === "correct",
  "The last mathematical answer remains Correct",
);
assert(
  questionStatusIsPendingGrade(loadingOverCorrect) ===
    true,
  "The pending question is still sitting on a Correct session",
);
assert(
  loadingOverCorrect.defaultStatus === "correct",
  "Grading state itself must remain Correct during loading",
);

const explanationView = presentTutorFeedback({
  questionLoading: false,
  status: "concept",
  feedback:
    "Може. Това уравнение може да се реши и с разделяне на променливите.",
  suggestion: "When you are ready, continue with the step.",
  lastGraded: previousCorrect,
});

assert(
  explanationView.explanation?.text.includes("Може.") ===
    true,
  "The conceptual response must be shown as an explanation",
);
assert(
  explanationView.graded?.status === "correct",
  "The previous Correct answer must remain visible separately",
);
assert(
  explanationView.showGradedAsLastAnswer === true,
  "Explanation view must label the grade as the last answer",
);
assert(
  explanationView.useDefaultPanel === false,
  "Explanation view must not use the graded-feedback layout",
);
assert(
  explanationView.showExplanationHeading === false,
  "Explanation responses must use one Explanation label, not a second heading",
);
assert(
  explanationView.explanation?.text.length > 0,
  "The explanation body must remain visible",
);
assert(
  explanationView.defaultStatus === "concept",
  "The session status for an explanation remains concept",
);

const englishExplanation = presentTutorFeedback({
  questionLoading: false,
  status: "concept",
  feedback: "Yes. Separation of variables also applies.",
  suggestion: null,
  lastGraded: previousCorrect,
});
assert(
  englishExplanation.showExplanationHeading === false,
  "English explanation responses also use a single Explanation label",
);
assert(
  englishExplanation.showGradedAsLastAnswer === true,
  "English explanation view still keeps the last graded answer",
);

const verifiedExplanation = presentTutorFeedback({
  questionLoading: false,
  status: "concept",
  feedback:
    "Да. Това уравнение може да се реши и чрез разделяне на променливите.\n\n    dy/dx = 2*(y + 1)",
  suggestion: "When you are ready, continue with the step.",
  lastGraded: previousCorrect,
});
assert(
  verifiedExplanation.showExplanationHeading === false,
  "Deterministic alternative-method answers use one Explanation label",
);
assert(
  verifiedExplanation.explanation?.text.includes(
    "разделяне на променливите",
  ) === true,
  "The deterministic explanation body remains visible",
);
assert(
  verifiedExplanation.showGradedAsLastAnswer === true,
  "Previous graded feedback stays separate from the explanation",
);
assert(
  verifiedExplanation.useDefaultPanel === false,
  "Deterministic explanations do not use the graded-feedback layout",
);

const waiting = presentTutorFeedback({
  questionLoading: false,
  status: "waiting_for_answer",
  feedback: "Find the integrating factor mu(x).",
  suggestion: null,
  lastGraded: null,
});

assert(
  waiting.useDefaultPanel === true,
  "Ordinary tutor prompts keep the default feedback panel",
);
assert(
  waiting.explanation === null,
  "Waiting for an answer is not an explanation",
);
assert(
  waiting.loadingExplanation === false,
  "Waiting for an answer is not question loading",
);
assert(
  waiting.useDefaultPanel === true,
  "Ordinary graded or waiting feedback keeps the feedback heading",
);

const gradedCorrect = presentTutorFeedback({
  questionLoading: false,
  status: "correct",
  feedback: "Correct. You found the integrating factor.",
  suggestion: "Next, multiply by mu(x).",
  lastGraded: previousCorrect,
});
assert(
  gradedCorrect.useDefaultPanel === true,
  "Ordinary graded feedback retains the default heading layout",
);
assert(
  gradedCorrect.explanation === null,
  "Ordinary graded feedback is not shown as an explanation",
);
assert(
  gradedCorrect.loadingExplanation === false,
  "Ordinary graded feedback is not the question loading state",
);

console.log("feedback_presentation tests passed");
