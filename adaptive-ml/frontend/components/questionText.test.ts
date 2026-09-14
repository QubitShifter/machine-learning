import {
  INITIAL_QUESTION_INTERACTION,
  closeQuestionMode,
  isAnswerEditorEnabled,
  openQuestionMode,
  prepareQuestionForSubmit,
  readQuestionFieldValue,
  submitQuestionMode,
  toggleQuestionMode,
} from "./questionText.ts";

function assert(
  condition: boolean,
  message: string,
): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

const bulgarianQuestion =
  "Защо ми е нужен интегриращ фактор?";
const englishQuestion =
  "Why do we use an integrating factor?";
const mixedQuestion = "Защо използваме μ(x)?";
const doubleSpaced =
  "Как  намираме  интегриращия  фактор?";

assert(
  readQuestionFieldValue(bulgarianQuestion) ===
    bulgarianQuestion,
  "Bulgarian question spaces must be preserved while typing",
);
assert(
  readQuestionFieldValue(englishQuestion) ===
    englishQuestion,
  "English question spaces must be preserved while typing",
);
assert(
  readQuestionFieldValue(mixedQuestion) ===
    mixedQuestion,
  "Mixed Bulgarian/math question text must stay unchanged",
);
assert(
  readQuestionFieldValue(doubleSpaced) ===
    doubleSpaced,
  "Internal multiple spaces must not be collapsed while typing",
);
assert(
  readQuestionFieldValue(
    "  Защо използваме μ(x)?  ",
  ) === "  Защо използваме μ(x)?  ",
  "Leading and trailing spaces stay until submit",
);

assert(
  prepareQuestionForSubmit(
    "  Защо ми е нужен интегриращ фактор?  ",
  ) === bulgarianQuestion,
  "Submit may trim ends but must keep internal spaces",
);
assert(
  prepareQuestionForSubmit(englishQuestion) ===
    englishQuestion,
  "English questions must submit unchanged",
);
assert(
  prepareQuestionForSubmit(
    "  Защо използваме μ(x)? ",
  ) === mixedQuestion,
  "Mixed Bulgarian/math questions must keep internal spaces on submit",
);
assert(
  prepareQuestionForSubmit(doubleSpaced) ===
    doubleSpaced,
  "Internal multiple spaces must survive submit",
);

const initialEditorEnabled = isAnswerEditorEnabled({
  questionMode: INITIAL_QUESTION_INTERACTION.questionMode,
  loading: false,
});
assert(
  INITIAL_QUESTION_INTERACTION.questionMode === false,
  "Initial question mode must be closed",
);
assert(
  initialEditorEnabled,
  "Answer editor must start enabled",
);

const opened = openQuestionMode(
  INITIAL_QUESTION_INTERACTION,
);
assert(
  opened.questionMode === true,
  "Opening the question form must enter question mode",
);
assert(
  isAnswerEditorEnabled({
    questionMode: opened.questionMode,
    loading: false,
  }) === false,
  "Answer editor must be disabled while the question form is open",
);

const submittedBulgarian = submitQuestionMode({
  questionMode: true,
  questionText: "  Защо ни е нужен интегриращ фактор?  ",
});
assert(
  submittedBulgarian.submittedQuestion ===
    "Защо ни е нужен интегриращ фактор?",
  "Successful submit must keep internal question spaces",
);
assert(
  submittedBulgarian.state.questionMode === false,
  "Successful submit must leave question mode",
);
assert(
  submittedBulgarian.state.questionText === "",
  "Successful submit must clear the question field",
);
assert(
  isAnswerEditorEnabled({
    questionMode: submittedBulgarian.state.questionMode,
    loading: false,
  }),
  "Answer editor must be enabled after a successful question submit",
);

const cancelled = closeQuestionMode(opened);
assert(
  cancelled.questionMode === false,
  "Closing the question form must leave question mode",
);
assert(
  isAnswerEditorEnabled({
    questionMode: cancelled.questionMode,
    loading: false,
  }),
  "Answer editor must be enabled after cancel/close",
);

const toggledClosed = toggleQuestionMode(opened);
assert(
  toggledClosed.questionMode === false,
  "Toggling Ask a question while open must close question mode",
);
assert(
  isAnswerEditorEnabled({
    questionMode: toggledClosed.questionMode,
    loading: false,
  }),
  "Answer editor must be enabled after toggling the question form closed",
);

const emptySubmit = submitQuestionMode({
  questionMode: true,
  questionText: "   ",
});
assert(
  emptySubmit.submittedQuestion === null,
  "Empty submit must not send a question",
);
assert(
  emptySubmit.state.questionMode === true,
  "Empty submit must keep question mode open for retry",
);
assert(
  isAnswerEditorEnabled({
    questionMode: emptySubmit.state.questionMode,
    loading: false,
  }) === false,
  "Answer editor stays disabled while the learner retries an empty question",
);

assert(
  isAnswerEditorEnabled({
    questionMode: false,
    loading: false,
  }),
  "MathLive answer handling stays enabled when question mode is off",
);
assert(
  isAnswerEditorEnabled({
    questionMode: false,
    loading: true,
  }) === false,
  "Loading still disables the answer editor when question mode is off",
);

console.log("question_text tests passed");
