import {
  presentSolvedStepDisplay,
  readCompletedResultLatex,
  readFinalResultLatex,
  readSolvedResults,
} from "./solvedResults.ts";

function assert(
  condition: boolean,
  message: string,
): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

const afterStepOneMetadata = {
  completed_result_latex: "2x = 12",
  solved_results: [
    { step_number: 1, result_latex: "2x = 12" },
  ],
};

assert(
  readSolvedResults(undefined).length === 0,
  "Missing metadata must not invent solved results",
);
assert(
  readCompletedResultLatex({}) === null,
  "Absence of result_latex must not invent a completed result",
);
assert(
  readFinalResultLatex({ final_answer: 6 }) === null,
  "Numeric final_answer must not be treated as result_latex",
);

const waiting = presentSolvedStepDisplay({
  status: "waiting_for_answer",
  completed: false,
  metadata: {},
});
assert(
  waiting.showHistoryBeforeCurrentStep === false,
  "A fresh session has no solved-step history",
);
assert(
  waiting.history.length === 0,
  "Unsolved current result remains hidden",
);
assert(
  waiting.finalResultLatex === null,
  "Waiting for an answer must not reveal a final result",
);

const afterFirstCorrect = presentSolvedStepDisplay({
  status: "correct",
  completed: false,
  metadata: afterStepOneMetadata,
});
assert(
  afterFirstCorrect.showHistoryBeforeCurrentStep === true,
  "Previous solved result appears before the current step",
);
assert(
  afterFirstCorrect.history.map((item) => item.resultLatex).join(
    "|",
  ) === "2x = 12",
  "After Step 1, 2x = 12 is the compact history above the next prompt",
);
assert(
  afterFirstCorrect.finalResultLatex === null,
  "The unsolved current result x = 6 stays hidden",
);

const nextStep = presentSolvedStepDisplay({
  status: "waiting_for_answer",
  completed: false,
  metadata: {
    solved_results: [
      { step_number: 1, result_latex: "2x = 12" },
    ],
  },
});
assert(
  nextStep.showHistoryBeforeCurrentStep === true,
  "The next step still shows prior solved history first",
);
assert(
  nextStep.history[0].resultLatex === "2x = 12",
  "Step 2 history shows that Step 1 produced 2x = 12",
);
assert(
  nextStep.finalResultLatex === null,
  "An unsolved current step does not show a final result",
);

const complete = presentSolvedStepDisplay({
  status: "complete",
  completed: true,
  metadata: {
    completed_result_latex: "x = 6",
    final_result_latex: "x = 6",
    solved_results: [
      { step_number: 1, result_latex: "2x = 12" },
      { step_number: 2, result_latex: "x = 6" },
    ],
  },
});
assert(
  complete.finalResultLatex === "x = 6",
  "Final result is shown prominently",
);
assert(
  complete.showSolutionSummary === true,
  "Earlier intermediate results remain in the solution summary",
);
assert(
  complete.history.map((item) => item.resultLatex).join("|") ===
    "2x = 12",
  "Duplicate final result is removed from solved history",
);
assert(
  complete.showHistoryBeforeCurrentStep === false,
  "Completion uses the summary, not the in-progress history slot",
);

const singleStepComplete = presentSolvedStepDisplay({
  status: "complete",
  completed: true,
  metadata: {
    completed_result_latex: "12 + 7 = 19",
    final_result_latex: "12 + 7 = 19",
    solved_results: [
      { step_number: 1, result_latex: "12 + 7 = 19" },
    ],
  },
});
assert(
  singleStepComplete.finalResultLatex === "12 + 7 = 19",
  "Single-step completion still shows the final result",
);
assert(
  singleStepComplete.history.length === 0,
  "Single-step completion has no leftover history items",
);
assert(
  singleStepComplete.showSolutionSummary === false,
  "Single-step completion does not render empty solved-history UI",
);

const catalog = presentSolvedStepDisplay({
  status: "correct",
  completed: false,
  metadata: {
    completed_step: 1,
    next_prompt: "What is the next number?",
  },
});
assert(
  catalog.history.length === 0,
  "Absence of result_latex does not invent history",
);
assert(
  catalog.showHistoryBeforeCurrentStep === false,
  "Problems without result_latex remain unchanged",
);
assert(
  catalog.showSolutionSummary === false,
  "Catalog problems without result_latex have no solution summary",
);

const catalogComplete = presentSolvedStepDisplay({
  status: "complete",
  completed: true,
  metadata: {
    completed_step: 7,
    final_answer: 116,
  },
});
assert(
  catalogComplete.finalResultLatex === null,
  "Completion without result_latex does not invent a final expression",
);
assert(
  catalogComplete.showSolutionSummary === false,
  "Catalog completion without result_latex has no solved-history UI",
);

console.log("solvedResults tests passed");
