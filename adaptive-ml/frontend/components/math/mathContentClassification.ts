const englishPromptWords =
  /\b(after|and|answer|as|ask|calculate|check|compare|compute|correct|differentiate|do|does|everything|find|first|for|form|from|hint|identify|inside|left|like|match|next|now|place|problem|result|right|should|side|solve|something|start|step|substitute|substitution|such|that|the|then|they|this|try|use|using|what|where|with|work|write|your)\b/i;

const mathTokenPattern =
  /(\\[a-zA-Z]+|\*\*|[=+\-*/^']|dy\/dx|d\/dx|exp\(|sqrt\(|integral\(|mu\(x\)|P\(x\)|Q\(x\)|e\^\{)/;

const MATH_IDENTIFIERS = new Set([
  "sin",
  "cos",
  "tan",
  "exp",
  "log",
  "ln",
  "sqrt",
  "integral",
  "mu",
  "dx",
  "dy",
]);

export function convertPlusMinus(
  value: string,
) {
  return value.replace(/\+\/-/g, "\\pm");
}

export function ordinaryLanguageWords(
  line: string,
) {
  const tokens = line.match(/\b[A-Za-z]+\b/g) ?? [];

  return tokens.filter((token) => {
    if (token.length === 1) {
      return false;
    }

    return !MATH_IDENTIFIERS.has(
      token.toLowerCase(),
    );
  });
}

export function looksLikeEnglishProse(
  line: string,
) {
  return ordinaryLanguageWords(line).length >= 2;
}

export function isMathOnlyLine(
  line: string,
) {
  const trimmed = line.trim();

  if (!trimmed) {
    return false;
  }

  if (looksLikeEnglishProse(trimmed)) {
    return false;
  }

  if (/^([xyzC]|\d+(?:\s*\/\s*\d+)?)$/.test(trimmed)) {
    return true;
  }

  return (
    mathTokenPattern.test(trimmed) &&
    !englishPromptWords.test(trimmed)
  );
}

export function lineUsesMathOnlyRenderer(
  line: string,
  forceMath = false,
) {
  return (
    forceMath ||
    line.startsWith("    ") ||
    isMathOnlyLine(line)
  );
}
