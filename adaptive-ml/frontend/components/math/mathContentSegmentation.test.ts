import {
  convertPlusMinus,
  isMathOnlyLine,
  lineUsesMathOnlyRenderer,
} from "./mathContentClassification.ts";
import { splitInlineMath } from "./mathContentSegmentation.ts";

function assert(
  condition: boolean,
  message: string,
): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function firstMathValue(
  line: string,
) {
  const math = splitInlineMath(line).find(
    (segment) => segment.type === "math",
  );

  assert(
    math !== undefined,
    `Expected a math fragment in: ${line}`,
  );

  return math.value;
}

function textBeforeFirstMath(
  line: string,
) {
  const segments = splitInlineMath(line);
  const mathIndex = segments.findIndex(
    (segment) => segment.type === "math",
  );

  assert(
    mathIndex > 0,
    `Expected prose before math in: ${line}`,
  );

  return segments
    .slice(0, mathIndex)
    .map((segment) => segment.value)
    .join("");
}

function textAfterFirstMath(
  line: string,
) {
  const segments = splitInlineMath(line);
  const mathIndex = segments.findIndex(
    (segment) => segment.type === "math",
  );

  assert(
    mathIndex >= 0 && mathIndex < segments.length - 1,
    `Expected prose after math in: ${line}`,
  );

  return segments
    .slice(mathIndex + 1)
    .map((segment) => segment.value)
    .join("");
}

function visibleBoundaryPreview(
  line: string,
) {
  return splitInlineMath(line)
    .map((segment) => {
      if (segment.type === "text") {
        return segment.value;
      }

      return convertPlusMinus(segment.value).replace(
        /\\pm/g,
        "±",
      );
    })
    .join("");
}

const simplifyExpression =
  "Simplify the expression exp(ln|y|).";
const plusMinusHint =
  "Use +/- to represent both possibilities.";
const renameConstant =
  "Since exp(C) is a positive constant, rename it as K.";
const absorbConstant =
  "Combine +/- K into one new arbitrary constant C.";

assert(
  textBeforeFirstMath(simplifyExpression) ===
    "Simplify the expression ",
  "Prose before exp(...) must keep the trailing space",
);
assert(
  firstMathValue(simplifyExpression) === "exp(ln|y|)",
  "Only the mathematical expression should be the math fragment",
);
assert(
  textBeforeFirstMath(simplifyExpression).includes(
    "the expression ",
  ),
  "the and expression must remain separate prose words",
);

assert(
  convertPlusMinus(firstMathValue(plusMinusHint)) ===
    "\\pm",
  "+/- must convert to \\pm",
);
assert(
  textAfterFirstMath(plusMinusHint).startsWith(" to"),
  "Following prose must preserve the space before to",
);
assert(
  visibleBoundaryPreview(plusMinusHint).includes(
    "± to",
  ),
  "The rendered boundary must keep a space after ±",
);
assert(
  visibleBoundaryPreview(plusMinusHint).includes(
    "±to",
  ) === false,
  "The result must not concatenate ± with to",
);

assert(
  textBeforeFirstMath(renameConstant) === "Since ",
  "Prose before exp(C) must keep its trailing space",
);
assert(
  firstMathValue(renameConstant) === "exp(C)",
  "exp(C) must be the inline math fragment",
);
assert(
  textAfterFirstMath(renameConstant).startsWith(" is "),
  "Prose after exp(C) must keep its leading space",
);

assert(
  convertPlusMinus(firstMathValue(absorbConstant)) ===
    "\\pm K",
  "+/- K must stay one math fragment and convert to \\pm K",
);
assert(
  textBeforeFirstMath(absorbConstant) === "Combine ",
  "Prose before +/- K must keep its trailing space",
);
assert(
  textAfterFirstMath(absorbConstant).startsWith(" into"),
  "Following prose after +/- K must keep the boundary space",
);

assert(
  isMathOnlyLine("y = +/- K*exp(x**2 / 2)") === true,
  "Bare equation lines must still be math-only",
);
assert(
  lineUsesMathOnlyRenderer(
    "y = +/- K*exp(x**2 / 2)",
  ) === true,
  "Bare equations must still use math-only rendering",
);
assert(
  isMathOnlyLine("sin x + cos x = tan x") === true,
  "Trigonometric expressions must remain math-only",
);
assert(
  isMathOnlyLine("exp(x) + log(x) = sqrt(x)") === true,
  "Named-function expressions must remain math-only",
);

const kinematicsStatement =
  "An object starts from rest and accelerates uniformly at $1\\ \\mathrm{m/s^2}$ for $2\\ \\mathrm{s}$.";
const kinematicsSegments = splitInlineMath(
  kinematicsStatement,
);
const kinematicsMath = kinematicsSegments.filter(
  (segment) => segment.type === "math",
);

assert(
  kinematicsMath[0]?.value === "1\\ \\mathrm{m/s^2}",
  "Dollar-delimited kinematics quantities must become math fragments",
);
assert(
  kinematicsMath[1]?.value === "2\\ \\mathrm{s}",
  "A second dollar-delimited quantity must also become math",
);
assert(
  kinematicsSegments.some(
    (segment) =>
      segment.type === "text" &&
      segment.value.includes(" uniformly at "),
  ),
  "Prose around dollar-delimited math must keep its spaces",
);
assert(
  kinematicsSegments.some(
    (segment) =>
      segment.type === "text" &&
      segment.value === " for ",
  ),
  "The word for between quantities must stay prose",
);
assert(
  kinematicsSegments.every(
    (segment) => !segment.value.includes("$"),
  ),
  "Dollar delimiters must not remain in visible segments",
);
assert(
  firstMathValue("Solve dy/dx = 2*x*y") ===
    "dy/dx = 2*x*y",
  "ODE statements without dollars must still segment",
);

const bulgarianKinematics =
  "Тяло тръгва от покой и се движи с постоянно ускорение $3\\ \\mathrm{m/s^2}$ в продължение на $4\\ \\mathrm{s}$.";
const bulgarianSegments = splitInlineMath(
  bulgarianKinematics,
);

assert(
  bulgarianSegments.some(
    (segment) =>
      segment.type === "text" &&
      segment.value.includes("постоянно ускорение"),
  ),
  "Cyrillic prose around math must stay visible text",
);
assert(
  firstMathValue(bulgarianKinematics) ===
    "3\\ \\mathrm{m/s^2}",
  "Bulgarian kinematics statements must still extract math",
);
assert(
  bulgarianSegments.some(
    (segment) =>
      segment.type === "text" &&
      segment.value.includes(" в продължение на "),
  ),
  "Cyrillic spacing around math must be preserved",
);

const bulgarianIdentifyPq =
  "След това определете P(x) и Q(x).";
const bulgarianIdentifySegments = splitInlineMath(
  bulgarianIdentifyPq,
);

assert(
  isMathOnlyLine(bulgarianIdentifyPq) === false,
  "Bulgarian P(x) Q(x) suggestion must not be one math line",
);
assert(
  bulgarianIdentifySegments.some(
    (segment) =>
      segment.type === "text" &&
      segment.value === "След това определете ",
  ),
  "Cyrillic prose before P(x) must keep its trailing space",
);
assert(
  bulgarianIdentifySegments.some(
    (segment) =>
      segment.type === "text" &&
      segment.value === " и ",
  ),
  "The Cyrillic conjunction around Q(x) must keep both spaces",
);
assert(
  bulgarianIdentifySegments.some(
    (segment) =>
      segment.type === "text" &&
      segment.value === ".",
  ),
  "The closing period must remain a text segment",
);
assert(
  bulgarianIdentifySegments.filter(
    (segment) => segment.type === "math",
  ).map((segment) => segment.value).join(",") ===
    "P(x),Q(x)",
  "P(x) and Q(x) must be the only math fragments",
);

const englishIdentifyPq =
  "Next, identify P(x) and Q(x).";
const englishIdentifySegments = splitInlineMath(
  englishIdentifyPq,
);

assert(
  isMathOnlyLine(englishIdentifyPq) === false,
  "English P(x) Q(x) suggestion must remain mixed content",
);
assert(
  textBeforeFirstMath(englishIdentifyPq) ===
    "Next, identify ",
  "English prose before P(x) must keep its trailing space",
);
assert(
  englishIdentifySegments.some(
    (segment) =>
      segment.type === "text" &&
      segment.value === " and ",
  ),
  "English and between P(x) and Q(x) must keep both spaces",
);

const bulgarianCompareQ =
  "Сравнете резултата с Q(x).";
assert(
  isMathOnlyLine(bulgarianCompareQ) === false,
  "Bulgarian compare-with-Q(x) must remain mixed content",
);
assert(
  textBeforeFirstMath(bulgarianCompareQ) ===
    "Сравнете резултата с ",
  "Prose before a single Q(x) must keep its trailing space",
);
assert(
  firstMathValue(bulgarianCompareQ) === "Q(x)",
  "Q(x) must be the inline math fragment",
);

const bulgarianVelocity =
  "Скоростта е $v = v_0 + at$.";
const velocitySegments = splitInlineMath(
  bulgarianVelocity,
);
assert(
  firstMathValue(bulgarianVelocity) === "v = v_0 + at",
  "Explicit $...$ inline math must still be extracted",
);
assert(
  velocitySegments.some(
    (segment) =>
      segment.type === "text" &&
      segment.value.includes("Скоростта е "),
  ),
  "Cyrillic prose before $...$ must keep its trailing space",
);
assert(
  velocitySegments.every(
    (segment) => !segment.value.includes("$"),
  ),
  "Dollar delimiters must not remain after explicit math",
);

assert(
  isMathOnlyLine("y' + P(x)y = Q(x)") === true,
  "Standalone standard-form equation must remain math-only",
);
assert(
  lineUsesMathOnlyRenderer("y' + P(x)y = Q(x)") ===
    true,
  "Standalone standard-form equation must use math-only rendering",
);

console.log("math_content_segmentation tests passed");
