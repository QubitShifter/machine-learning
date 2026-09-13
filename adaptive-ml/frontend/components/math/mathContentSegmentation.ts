const englishPromptWords =
  /\b(after|and|answer|as|ask|calculate|check|compare|compute|correct|differentiate|do|does|everything|find|first|for|form|from|hint|identify|inside|left|like|match|next|now|place|problem|result|right|should|side|solve|something|start|step|substitute|substitution|such|that|the|then|they|this|try|use|using|what|where|with|work|write|your)\b/i;

const inlineMathPatterns: RegExp[] = [
  /\+\/-\s*[A-Za-z]\b/g,
  /\+\/-/g,
  /y'\s*\+\s*P\(x\)y\s*=\s*Q\(x\)/g,
  /d\/dx\([^)]*\)\s*(?:[+\-*/^=]\s*[^,.;:!?]+)+/g,
  /dy\/dx\s*(?:[+\-*/^=]\s*[^,.;:!?]+)+/g,
  /\by\s*=\s*(?:(?!\s(?:with|where|and|so|because|from|to)\b)[^,.;:!?])+/g,
  /\|[^|]+\|\s*(?:[+\-*/^=]\s*[^,.;:!?]+)+/g,
  /(?:mu|P|Q)\(x\)\s*(?:[+\-*/^=]\s*[^,.;:!?]+)+/g,
  /integral\(.+\)\s*dx/g,
  /exp\([^)]*\)/g,
  /sqrt\([^)]*\)/g,
  /\b\d+\s*\/\s*\d+\b/g,
  /\b[A-Za-z0-9()]+\s*\*\*\s*[-+]?[A-Za-z0-9()]+\b/g,
  /(?:mu|P|Q)\(x\)/g,
  /dy\/dx/g,
];

export interface MathSegment {
  type: "text" | "math";
  value: string;
}

function trimTrailingPunctuation(value: string) {
  const match = value.match(/^(.+?)([,.!?;:]+)?$/);

  return {
    body: match?.[1] ?? value,
    punctuation: match?.[2] ?? "",
  };
}

function findNextMathFragment(
  text: string,
  startIndex: number,
) {
  let bestMatch:
    | { index: number; raw: string }
    | null = null;

  for (const pattern of inlineMathPatterns) {
    pattern.lastIndex = startIndex;
    const match = pattern.exec(text);

    if (!match) {
      continue;
    }

    const raw = match[0];
    const value = raw.trim();

    if (!value || englishPromptWords.test(value)) {
      continue;
    }

    if (
      bestMatch === null ||
      match.index < bestMatch.index ||
      (match.index === bestMatch.index &&
        raw.length > bestMatch.raw.length)
    ) {
      bestMatch = {
        index: match.index,
        raw,
      };
    }
  }

  return bestMatch;
}

export function splitInlineMath(
  line: string,
): MathSegment[] {
  const segments: MathSegment[] = [];
  let cursor = 0;

  while (cursor < line.length) {
    const nextMatch = findNextMathFragment(
      line,
      cursor,
    );

    if (!nextMatch) {
      segments.push({
        type: "text",
        value: line.slice(cursor),
      });
      break;
    }

    const leadingWhitespace =
      nextMatch.raw.match(/^\s*/)?.[0] ?? "";
    const trailingWhitespace =
      nextMatch.raw.match(/\s*$/)?.[0] ?? "";
    const mathCore = nextMatch.raw.slice(
      leadingWhitespace.length,
      nextMatch.raw.length - trailingWhitespace.length,
    );
    const prefix = `${line.slice(
      cursor,
      nextMatch.index,
    )}${leadingWhitespace}`;

    if (prefix.length > 0) {
      segments.push({
        type: "text",
        value: prefix,
      });
    }

    const { body, punctuation } =
      trimTrailingPunctuation(mathCore);

    if (body.length > 0) {
      segments.push({
        type: "math",
        value: body,
      });
    }

    const suffix = `${punctuation}${trailingWhitespace}`;

    if (suffix.length > 0) {
      segments.push({
        type: "text",
        value: suffix,
      });
    }

    cursor = nextMatch.index + nextMatch.raw.length;
  }

  return segments.filter(
    (segment) => segment.value.length > 0,
  );
}
