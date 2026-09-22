import {
  answerPreservedAfterHint,
  feedbackPanelKey,
  hintButtonDisabled,
  hintButtonLabelKey,
} from "./hintControls.ts";
import { en } from "../i18n/en.ts";
import { bg } from "../i18n/bg.ts";
import type { TutorSession } from "../types/tutor.ts";

function assert(
  condition: boolean,
  message: string,
): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function session(
  overrides: Partial<TutorSession> = {},
): TutorSession {
  return {
    session_id: "s1",
    problem_id: "p1",
    problem_title: "Bottles",
    problem_statement: "A crate had bottles.",
    status: "waiting_for_answer",
    feedback: "How many bottles were there at the end?",
    current_step: 2,
    total_steps: 4,
    completed: false,
    hint_available: true,
    expected_input_type: "number",
    suggestion: null,
    metadata: {},
    ...overrides,
  };
}

assert(
  hintButtonLabelKey(session()) === "tutor.hint",
  "The first control is Hint",
);
assert(
  hintButtonLabelKey(
    session({
      metadata: { hints_used_on_step: 1 },
    }),
  ) === "tutor.moreHelp",
  "After the first hint the control becomes More help",
);
assert(
  hintButtonDisabled(
    session({
      hint_available: false,
      metadata: { hint_exhausted: true, hints_used_on_step: 3 },
    }),
  ),
  "The final hint disables More help",
);
assert(
  hintButtonDisabled(
    session({
      status: "concept",
      hint_available: false,
      metadata: {
        concept_question: true,
        answer_source: "local",
      },
    }),
  ),
  "A Guided Question without hint_level must not re-enable exhausted hints",
);
assert(
  hintButtonDisabled(
    session({
      current_step: 2,
      hint_available: true,
      metadata: {},
    }),
  ) === false,
  "The next step makes Hint available again",
);
assert(
  answerPreservedAfterHint("18", "18"),
  "A typed number stays after a hint click",
);
assert(
  feedbackPanelKey(
    session({
      status: "hint",
      feedback: "Level 1 text",
      metadata: { hint_level: 1, hints_used_on_step: 1 },
    }),
  ) !==
    feedbackPanelKey(
      session({
        status: "hint",
        feedback: "Level 2 text",
        metadata: { hint_level: 2, hints_used_on_step: 2 },
      }),
    ),
  "A later hint on the same step must remount feedback",
);
assert(
  en["tutor.moreHelp"] === "More help",
  "English more-help label is localized",
);
assert(
  bg["tutor.moreHelp"] === "Още помощ",
  "Bulgarian more-help label is localized",
);

console.log("hintControls tests passed");
