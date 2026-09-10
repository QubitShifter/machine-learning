"use client";

import type { ReactNode } from "react";
import katex from "katex";

interface MathContentProps {
  text: string | null | undefined;
  className?: string;
  forceMath?: boolean;
}

interface MathSegment {
  type: "text" | "math";
  value: string;
}

const katexOptions = {
  throwOnError: false,
  strict: "ignore" as const,
  trust: false,
  output: "htmlAndMathml" as const,
};

const englishPromptWords =
  /\b(after|and|answer|ask|calculate|check|compare|compute|correct|differentiate|do|does|everything|find|first|for|from|hint|identify|inside|left|match|next|now|place|problem|result|right|should|side|solve|start|step|substitute|substitution|that|the|then|they|this|use|using|what|where|with|work|your)\b/i;

const mathTokenPattern =
  /(\\[a-zA-Z]+|\*\*|[=+\-*/^']|dy\/dx|d\/dx|exp\(|sqrt\(|integral\(|mu\(x\)|P\(x\)|Q\(x\)|e\^\{)/;

const inlineMathPatterns: RegExp[] = [
  /y'\s*\+\s*P\(x\)y\s*=\s*Q\(x\)/g,
  /d\/dx\([^)]*\)\s*(?:[+\-*/^=]\s*[^,.;:!?]+)+/g,
  /dy\/dx\s*(?:[+\-*/^=]\s*[^,.;:!?]+)+/g,
  /\by\s*=\s*(?:(?!\s(?:with|where|and|so|because|from|to)\b)[^,.;:!?])+/g,
  /(?:mu|P|Q)\(x\)\s*(?:[+\-*/^=]\s*[^,.;:!?]+)+/g,
  /integral\(.+\)\s*dx/g,
  /exp\([^)]*\)/g,
  /sqrt\([^)]*\)/g,
  /\b\d+\s*\/\s*\d+\b/g,
  /\b[A-Za-z0-9()]+\s*\*\*\s*[-+]?[A-Za-z0-9()]+\b/g,
  /(?:mu|P|Q)\(x\)/g,
  /dy\/dx/g,
];

function trimTrailingPunctuation(value: string) {
  const match = value.match(/^(.+?)([,.!?;:]+)?$/);

  return {
    body: match?.[1] ?? value,
    punctuation: match?.[2] ?? "",
  };
}

function convertFunctionCalls(
  value: string,
  name: "exp" | "sqrt",
  formatter: (argument: string) => string,
) {
  const prefix = `${name}(`;
  let output = "";
  let index = 0;

  while (index < value.length) {
    const start = value.indexOf(prefix, index);

    if (start === -1) {
      output += value.slice(index);
      break;
    }

    output += value.slice(index, start);

    let depth = 1;
    let cursor = start + prefix.length;

    while (cursor < value.length && depth > 0) {
      if (value[cursor] === "(") {
        depth += 1;
      } else if (value[cursor] === ")") {
        depth -= 1;
      }

      cursor += 1;
    }

    if (depth !== 0) {
      output += value.slice(start);
      break;
    }

    const argument = value.slice(
      start + prefix.length,
      cursor - 1,
    );
    output += formatter(argument);
    index = cursor;
  }

  return output;
}

function convertDerivativeCalls(value: string) {
  const prefix = "d/dx(";
  let output = "";
  let index = 0;

  while (index < value.length) {
    const start = value.indexOf(prefix, index);

    if (start === -1) {
      output += value.slice(index);
      break;
    }

    output += value.slice(index, start);

    const endIndex = findMatchingDelimiter(
      value,
      start + prefix.length - 1,
      "(",
      ")",
    );

    if (endIndex === -1) {
      output += value.slice(start);
      break;
    }

    const argument = value.slice(
      start + prefix.length,
      endIndex,
    );
    output += `\\frac{d}{dx}\\left(${convertMathNotation(
      argument,
    )}\\right)`;
    index = endIndex + 1;
  }

  return output;
}

function findMatchingDelimiter(
  value: string,
  startIndex: number,
  open: string,
  close: string,
) {
  let depth = 0;

  for (
    let index = startIndex;
    index < value.length;
    index += 1
  ) {
    if (value[index] === open) {
      depth += 1;
    } else if (value[index] === close) {
      depth -= 1;

      if (depth === 0) {
        return index;
      }
    }
  }

  return -1;
}

function readPowerExponent(value: string, startIndex: number) {
  const first = value[startIndex];

  if (first === "{") {
    const endIndex = findMatchingDelimiter(
      value,
      startIndex,
      "{",
      "}",
    );

    if (endIndex === -1) {
      return null;
    }

    return {
      exponent: value.slice(startIndex + 1, endIndex),
      endIndex: endIndex + 1,
    };
  }

  if (first === "(") {
    const endIndex = findMatchingDelimiter(
      value,
      startIndex,
      "(",
      ")",
    );

    if (endIndex === -1) {
      return null;
    }

    return {
      exponent: value.slice(startIndex + 1, endIndex),
      endIndex: endIndex + 1,
    };
  }

  const match = value
    .slice(startIndex)
    .match(/^[-+]?[A-Za-z0-9]+/);

  if (!match) {
    return null;
  }

  return {
    exponent: match[0],
    endIndex: startIndex + match[0].length,
  };
}

function convertPowers(value: string) {
  const normalized = value.replace(/\*\*/g, "^");
  let output = "";
  let index = 0;

  while (index < normalized.length) {
    if (normalized[index] !== "^") {
      output += normalized[index];
      index += 1;
      continue;
    }

    const exponent = readPowerExponent(
      normalized,
      index + 1,
    );

    if (!exponent) {
      output += normalized[index];
      index += 1;
      continue;
    }

    output += `^{${convertMathNotation(
      exponent.exponent,
    )}}`;
    index = exponent.endIndex;
  }

  return output;
}

export function convertMathNotation(value: string): string {
  const trimmed = value.trim();

  if (!trimmed) {
    return trimmed;
  }

  let output = trimmed
    .replace(/\\times/g, "\\cdot")
    .replace(/dy\/dx/g, "\\frac{dy}{dx}")
    .replace(/(^|[^\\])\bmu\b/g, "$1\\mu");

  output = convertDerivativeCalls(output);

  output = output.replace(
    /integral\((.+)\)\s*dx/g,
    (_match, integrand: string) =>
      `\\int ${convertMathNotation(integrand)}\\, dx`,
  );

  output = convertFunctionCalls(
    output,
    "exp",
    (argument) =>
      `e^{${convertMathNotation(argument)}}`,
  );
  output = convertFunctionCalls(
    output,
    "sqrt",
    (argument) =>
      `\\sqrt{${convertMathNotation(argument)}}`,
  );
  output = convertPowers(output);

  output = output.replace(
    /\b(\d+)\s*\/\s*(\d+)\b/g,
    "\\frac{$1}{$2}",
  );
  output = output.replace(/\*/g, "\\,");

  return output;
}

function isMathOnlyLine(line: string) {
  const trimmed = line.trim();

  if (!trimmed) {
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

function findNextMathFragment(
  text: string,
  startIndex: number,
) {
  let bestMatch:
    | { index: number; value: string }
    | null = null;

  for (const pattern of inlineMathPatterns) {
    pattern.lastIndex = startIndex;
    const match = pattern.exec(text);

    if (!match) {
      continue;
    }

    const value = match[0].trim();

    if (!value || englishPromptWords.test(value)) {
      continue;
    }

    if (
      bestMatch === null ||
      match.index < bestMatch.index ||
      (match.index === bestMatch.index &&
        value.length > bestMatch.value.length)
    ) {
      bestMatch = {
        index: match.index,
        value,
      };
    }
  }

  return bestMatch;
}

function splitInlineMath(line: string): MathSegment[] {
  const segments: MathSegment[] = [];
  let cursor = 0;

  while (cursor < line.length) {
    const nextMatch = findNextMathFragment(line, cursor);

    if (!nextMatch) {
      segments.push({
        type: "text",
        value: line.slice(cursor),
      });
      break;
    }

    if (nextMatch.index > cursor) {
      segments.push({
        type: "text",
        value: line.slice(cursor, nextMatch.index),
      });
    }

    const rawValue = line.slice(
      nextMatch.index,
      nextMatch.index + nextMatch.value.length,
    );
    const { body, punctuation } =
      trimTrailingPunctuation(rawValue);

    segments.push({
      type: "math",
      value: body,
    });

    if (punctuation) {
      segments.push({
        type: "text",
        value: punctuation,
      });
    }

    cursor = nextMatch.index + rawValue.length;
  }

  return segments.filter((segment) => segment.value.length > 0);
}

function KatexSpan({
  latex,
  displayMode,
}: {
  latex: string;
  displayMode: boolean;
}) {
  const rendered = katex.renderToString(latex, {
    ...katexOptions,
    displayMode,
  });

  // The markup comes only from KaTeX with trust disabled; backend strings are
  // passed as math input, never as raw HTML.
  return (
    <span
      className={
        displayMode ? "math-display" : "math-inline"
      }
      dangerouslySetInnerHTML={{
        __html: rendered,
      }}
    />
  );
}

function renderInlineSegments(
  segments: MathSegment[],
  keyPrefix: string,
) {
  return segments.map((segment, index) => {
    if (segment.type === "math") {
      return (
        <KatexSpan
          displayMode={false}
          key={`${keyPrefix}-math-${index}`}
          latex={convertMathNotation(segment.value)}
        />
      );
    }

    return (
      <span key={`${keyPrefix}-text-${index}`}>
        {segment.value}
      </span>
    );
  });
}

function renderLine(
  line: string,
  index: number,
  forceMath: boolean,
): ReactNode {
  const trimmed = line.trim();

  if (!trimmed) {
    return <br key={`line-${index}`} />;
  }

  if (forceMath || line.startsWith("    ") || isMathOnlyLine(line)) {
    return (
      <p className="math-content-block" key={`line-${index}`}>
        <KatexSpan
          displayMode
          latex={convertMathNotation(trimmed)}
        />
      </p>
    );
  }

  const solveMatch = trimmed.match(
    /^(Solve|Find|Calculate|Compute|Simplify|Verify)\s+(.+?)([.!?])?$/i,
  );

  if (solveMatch && mathTokenPattern.test(solveMatch[2])) {
    return (
      <p key={`line-${index}`}>
        {solveMatch[1]}{" "}
        <KatexSpan
          displayMode={false}
          latex={convertMathNotation(solveMatch[2])}
        />
        {solveMatch[3] ?? ""}
      </p>
    );
  }

  return (
    <p key={`line-${index}`}>
      {renderInlineSegments(
        splitInlineMath(line),
        `line-${index}`,
      )}
    </p>
  );
}

export function MathContent({
  text,
  className,
  forceMath = false,
}: MathContentProps) {
  const lines = (text ?? "").split(/\r?\n/);

  return (
    <div className={className ?? "math-content"}>
      {lines.map((line, index) =>
        renderLine(line, index, forceMath),
      )}
    </div>
  );
}
