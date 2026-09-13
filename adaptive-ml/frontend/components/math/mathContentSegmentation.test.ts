import {
  convertPlusMinus,
  isMathOnlyLine,
  lineUsesMathOnlyRenderer,
} from "./mathContentClassification";
import { splitInlineMath } from "./mathContentSegmentation";

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

console.log("math_content_segmentation tests passed");
