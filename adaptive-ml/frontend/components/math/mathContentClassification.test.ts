import {
  convertPlusMinus,
  isMathOnlyLine,
  lineUsesMathOnlyRenderer,
} from "./mathContentClassification.ts";

const absorbConstantInstruction =
  "Combine +/- K into one new arbitrary constant C.";

function assert(
  condition: boolean,
  message: string,
) {
  if (!condition) {
    throw new Error(message);
  }
}

assert(
  isMathOnlyLine(absorbConstantInstruction) === false,
  "Absorb-constant instruction must remain prose",
);
assert(
  lineUsesMathOnlyRenderer(absorbConstantInstruction) ===
    false,
  "Absorb-constant instruction must not use the math-only renderer",
);
assert(
  isMathOnlyLine("y = +/- K*exp(x**2 / 2)") === true,
  "Bare equation lines must still be math-only",
);
assert(
  isMathOnlyLine("sin x + cos x = tan x") === true,
  "Trigonometric expressions must remain math-only",
);
assert(
  isMathOnlyLine("exp(x) + log(x) = sqrt(x)") === true,
  "Named-function expressions must remain math-only",
);
assert(
  isMathOnlyLine(
    "Substitute x into the equation and simplify.",
  ) === false,
  "English sentences with a math token must remain prose",
);
assert(
  lineUsesMathOnlyRenderer(
    "    y = +/- K*exp(x**2 / 2)",
  ) === true,
  "Indented equations must still use the math-only renderer",
);
assert(
  convertPlusMinus("+/- K") === "\\pm K",
  "+/- in math fragments must become \\pm",
);
assert(
  convertPlusMinus("y = +/- K*exp(x)") ===
    "y = \\pm K*exp(x)",
  "+/- conversion must apply inside equation fragments",
);

const bulgarianIdentifyPq =
  "След това определете P(x) и Q(x).";
const englishIdentifyPq =
  "Next, identify P(x) and Q(x).";
const bulgarianCompareQ =
  "Сравнете резултата с Q(x).";

assert(
  isMathOnlyLine(bulgarianIdentifyPq) === false,
  "Bulgarian mixed prose with P(x) and Q(x) must not be math-only",
);
assert(
  lineUsesMathOnlyRenderer(bulgarianIdentifyPq) ===
    false,
  "Bulgarian mixed prose must not use the math-only renderer",
);
assert(
  isMathOnlyLine(englishIdentifyPq) === false,
  "English mixed prose with P(x) and Q(x) must not be math-only",
);
assert(
  isMathOnlyLine(bulgarianCompareQ) === false,
  "Bulgarian prose containing one expression must not be math-only",
);
assert(
  isMathOnlyLine("Намерете mu(x).") === false,
  "A Cyrillic instruction around mu(x) must remain prose",
);
assert(
  isMathOnlyLine("y' + P(x)y = Q(x)") === true,
  "Standalone linear standard form must remain math-only",
);
assert(
  lineUsesMathOnlyRenderer("y' + P(x)y = Q(x)") ===
    true,
  "Standalone linear standard form must use math-only rendering",
);
assert(
  isMathOnlyLine(
    "Да, това уравнение може да се реши и с разделяне на променливите, защото dy/dx + (2*x)*y = x.",
  ) === false,
  "Bulgarian mixed prose with an ODE must not be math-only",
);

console.log("math_content_classification tests passed");
