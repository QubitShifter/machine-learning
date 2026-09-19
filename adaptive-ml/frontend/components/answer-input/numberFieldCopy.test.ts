import { translate } from "../../i18n/index.ts";
import {
  isNumericAnswerField,
  numericAnswerNoteKey,
  numericAnswerPlaceholderKey,
} from "./numberFieldCopy.ts";

function assert(
  condition: boolean,
  message: string,
): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

assert(
  isNumericAnswerField("number") === true,
  "Number input type must use numeric-field guidance",
);
assert(
  isNumericAnswerField("text") === false,
  "Text input type must keep the generic answer note",
);
assert(
  isNumericAnswerField("math") === false,
  "Math input type must keep the math editor note",
);
assert(
  isNumericAnswerField("units") === false,
  "Units input type must keep the units note",
);
assert(
  numericAnswerNoteKey("number") === "tutor.numberFieldHint",
  "Numeric fields must point questions to Ask a question",
);
assert(
  numericAnswerNoteKey("text") === "tutor.expectedInput",
  "Legacy text fields must keep expected-input copy",
);
assert(
  numericAnswerPlaceholderKey("number") ===
    "tutor.placeholderNumber",
  "Numeric fields must use a number placeholder",
);

const englishHint = translate("en", "tutor.numberFieldHint");
const bulgarianHint = translate("bg", "tutor.numberFieldHint");

assert(
  englishHint.includes("Ask a question"),
  "English number-field hint must name Ask a question",
);
assert(
  englishHint.toLowerCase().includes("number"),
  "English number-field hint must mention a number",
);
assert(
  bulgarianHint.includes("Задай въпрос"),
  "Bulgarian number-field hint must name Задай въпрос",
);
assert(
  bulgarianHint.includes("число"),
  "Bulgarian number-field hint must mention a number",
);
assert(
  !englishHint.toLowerCase().includes("submit"),
  "Number-field hint must not auto-route text to a model",
);

console.log("number field copy tests passed");
